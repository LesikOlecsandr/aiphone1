from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Device, Estimate, Lead, MediaAsset, PartType, PartsPrice, PriceSource, QualityTier, ServiceLabor
from app.schemas.device import DeviceRead
from app.schemas.estimate import EstimateResponse, PriceRange
from app.services.device_matcher import DeviceMatcherService
from app.services.polish_gemini_service import PolishGeminiService
from app.services.repair_catalog_service import RepairCatalogService
from app.services.settings_service import SettingsService


@dataclass
class EstimateContext:
    lead: Lead | None
    device: Device
    mime_type: str
    media_path: str


class EstimateService:
    """Польский сервис расчёта ремонта с fallback через Google Search."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings_service = SettingsService(db)
        self.matcher = DeviceMatcherService(db)
        self.gemini = PolishGeminiService()
        self.repairs = RepairCatalogService(db)

    def resolve_context(self, lead_id: int | None, model_name: str | None, media_path: str, mime_type: str) -> EstimateContext:
        """Собирает контекст расчёта по заявке, модели и медиа."""

        lead = None
        if lead_id is not None:
            from app.models import Lead as LeadModel

            lead = self.db.query(LeadModel).filter(LeadModel.id == lead_id).one_or_none()
            if lead and not model_name:
                model_name = lead.device_model_raw

        if not model_name:
            raise ValueError("Brak modelu urzadzenia.")
        device = self.matcher.find_best_match(model_name)
        if device is None:
            raise ValueError("Nie znaleziono modelu urzadzenia w katalogu.")
        return EstimateContext(lead=lead, device=device, mime_type=mime_type, media_path=media_path)

    def create_estimate_for_media(self, lead_id: int | None, media_asset_id: int, model_name: str | None) -> EstimateResponse:
        """Строит оценку по ранее сохранённому media asset."""

        asset = self.db.query(MediaAsset).filter(MediaAsset.id == media_asset_id).one_or_none()
        if asset is None:
            raise ValueError("Nie znaleziono zalaczonego pliku.")
        return self.create_estimate(
            lead_id=lead_id,
            model_name=model_name,
            media_path=asset.storage_path,
            mime_type=asset.mime_type,
        )

    def create_estimate(self, lead_id: int | None, model_name: str, media_path: str, mime_type: str) -> EstimateResponse:
        """Выполняет анализ media, находит цену и возвращает польский расчёт."""

        context = self.resolve_context(lead_id, model_name, media_path, mime_type)
        diagnosis = self.gemini.analyze_media(media_path=media_path, mime_type=mime_type)
        if not diagnosis.is_smartphone:
            raise ValueError("Na przeslanych materialach nie rozpoznano smartfona.")
        if diagnosis.damage_category == "unknown":
            raise ValueError("Nie udalo sie jednoznacznie okreslic uszkodzenia.")

        if context.lead:
            context.lead.device_model_raw = f"{context.device.brand} {context.device.model_name}"
            context.lead.matched_device_id = context.device.id
            if not context.lead.problem_summary or len(diagnosis.technical_summary) > len(context.lead.problem_summary or ""):
                context.lead.problem_summary = diagnosis.technical_summary

        part_type = PartType(diagnosis.damage_category)
        settings_row = self.settings_service.get_or_create()
        labor = self.db.query(ServiceLabor).filter(ServiceLabor.part_type == part_type).one_or_none()
        if labor is None:
            raise ValueError("Brak skonfigurowanej robocizny dla tego typu naprawy.")

        catalog_hint = self.repairs.find_strict_match(
            self._build_catalog_lookup_text(context.device, diagnosis.damage_category, diagnosis.technical_summary)
        )

        prices = (
            self.db.query(PartsPrice)
            .filter(PartsPrice.device_id == context.device.id, PartsPrice.part_type == part_type)
            .all()
        )
        labor_hours = round(max(labor.base_labor_cost, 1) / max(settings_row.hourly_rate, 1), 2)
        labor_minutes = round(labor_hours * 60, 2)

        if prices:
            ranked = sorted(prices, key=lambda item: self._quality_rank(item.quality_tier))
            copy_part = ranked[0]
            original_part = ranked[-1]
            min_total = self._formula(copy_part.purchase_price, settings_row.hourly_rate, labor_hours, settings_row.parts_margin, settings_row.tax_multiplier)
            max_total = self._formula(original_part.purchase_price, settings_row.hourly_rate, labor_hours, settings_row.parts_margin, settings_row.tax_multiplier)
            recommended = round((min_total + max_total) / 2, 2)
            if catalog_hint is not None:
                min_total, max_total, recommended = self._apply_catalog_anchor(
                    min_total=min_total,
                    max_total=max_total,
                    catalog_price=catalog_hint.base_price,
                )
            market_hint = self._find_market_repair_price(context.device, part_type)
            if market_hint is not None and catalog_hint is None:
                min_total, max_total, recommended = self._blend_with_market_prices(
                    min_total=min_total,
                    max_total=max_total,
                    market_price=market_hint.repair_price,
                    brand=context.device.brand,
                )
            response = EstimateResponse(
                requested_model=model_name,
                matched_device=DeviceRead.model_validate(context.device),
                vision_result=diagnosis,
                price_range=PriceRange(
                    min_price=min_total,
                    max_price=max_total,
                    currency="PLN",
                    min_quality_tier="copy",
                    max_quality_tier="original",
                ),
                recommended_price=recommended,
                markup_factor=settings_row.parts_margin,
                price_source=(
                    PriceSource.GOOGLE_SEARCH.value
                    if market_hint is not None and self._should_label_as_market_source(context.device.brand) and catalog_hint is None
                    else PriceSource.DATABASE.value
                ),
                source_url=market_hint.source_url if market_hint is not None else None,
                labor_minutes_used=labor_minutes,
                customer_message=self._build_customer_message(
                    used_market_hint=market_hint is not None,
                    brand=context.device.brand,
                    used_catalog_hint=catalog_hint is not None,
                ),
            )
            self._save_estimate(
                response,
                context,
                diagnosis,
                (
                    PriceSource.GOOGLE_SEARCH
                    if market_hint is not None and self._should_label_as_market_source(context.device.brand) and catalog_hint is None
                    else PriceSource.DATABASE
                ),
                market_hint.source_url if market_hint is not None else None,
                labor_minutes,
                None,
            )
            return response

        google_price = self.gemini.search_part_price(context.device, part_type, self.db)
        total = self._formula(google_price.part_price, settings_row.hourly_rate, labor_hours, 1.0, settings_row.tax_multiplier)
        response = EstimateResponse(
            requested_model=model_name,
            matched_device=DeviceRead.model_validate(context.device),
            vision_result=diagnosis,
            price_range=PriceRange(
                min_price=round(total * 0.95, 2),
                max_price=round(total * 1.05, 2),
                currency="PLN",
                min_quality_tier="google_search",
                max_quality_tier="google_search",
            ),
            recommended_price=total,
            markup_factor=1.0,
            price_source=PriceSource.GOOGLE_SEARCH.value,
            source_url=google_price.source_url,
            labor_minutes_used=labor_minutes,
            customer_message="Cena czesci pochodzi z wyszukiwania Google na polskich stronach.",
        )
        self._save_estimate(
            response,
            context,
            diagnosis,
            PriceSource.GOOGLE_SEARCH,
            google_price.source_url,
            labor_minutes,
            google_price.part_price,
        )
        return response

    @staticmethod
    def _formula(part_price: float, hourly_rate: float, labor_hours: float, parts_margin: float, tax_multiplier: float) -> float:
        return round(((part_price * parts_margin) + (labor_hours * hourly_rate)) * tax_multiplier, 2)

    @staticmethod
    def _quality_rank(quality_tier: QualityTier) -> int:
        return {
            QualityTier.COPY: 0,
            QualityTier.REFURBISHED: 1,
            QualityTier.ORIGINAL: 2,
        }[quality_tier]

    def _find_market_repair_price(self, device: Device, part_type: PartType):
        """Dla rynkowych korekt probuje znalezc cene gotowej uslugi u konkurencji."""

        try:
            return self.gemini.search_competitor_repair_price(device, part_type, self.db)
        except Exception:
            return None

    @staticmethod
    def _blend_with_market_prices(min_total: float, max_total: float, market_price: float, brand: str) -> tuple[float, float, float]:
        """Lagodzi lokalna wycene benchmarkiem rynkowym, najmocniej dla Apple."""

        apple_bias = brand.lower() == "apple"
        market_min = round(market_price * (0.96 if apple_bias else 0.96), 2)
        market_max = round(market_price * (1.01 if apple_bias else 1.07), 2)
        if apple_bias:
            tuned_min = min(min_total, market_min)
            tuned_max = market_max
        else:
            tuned_min = round((min_total + market_min) / 2, 2)
            tuned_max = round((max_total + market_max) / 2, 2)
        tuned_min = min(tuned_min, tuned_max)
        tuned_max = max(tuned_max, tuned_min)
        recommended = round((tuned_min + tuned_max) / 2, 2)
        return tuned_min, tuned_max, recommended

    @staticmethod
    def _should_label_as_market_source(brand: str) -> bool:
        """Dla Apple pokazuje, ze cena byla dodatkowo sprawdzona rynkowo."""

        return brand.lower() == "apple"

    @staticmethod
    def _apply_catalog_anchor(min_total: float, max_total: float, catalog_price: float) -> tuple[float, float, float]:
        """Dopasowuje wycene do konkretnej pozycji z katalogu napraw."""

        anchored_min = round(min(min_total, catalog_price * 0.98), 2)
        anchored_max = round(min(max_total, catalog_price * 1.04), 2)
        if anchored_max < anchored_min:
            anchored_max = anchored_min
        return anchored_min, anchored_max, round((anchored_min + anchored_max) / 2, 2)

    @staticmethod
    def _build_catalog_lookup_text(device: Device, damage_category: str, technical_summary: str) -> str:
        """Buduje bogatszy tekst do szukania gotowych pozycji w katalogu napraw."""

        synonyms = {
            "screen": "ekran wyswietlacz display",
            "glass_only": "szklo szybka szybka ekranu",
            "body": "plecy klapka tyl tylna szybka obudowa",
            "battery": "bateria akumulator",
        }
        return " ".join(
            filter(
                None,
                [
                    device.brand,
                    device.model_name,
                    damage_category,
                    synonyms.get(damage_category, ""),
                    technical_summary,
                ],
            )
        )

    @staticmethod
    def _build_customer_message(used_market_hint: bool, brand: str, used_catalog_hint: bool = False) -> str:
        """Buduje krotki opis zrodla wyceny dla klienta."""

        if used_catalog_hint:
            return "Wycena zostala oparta na pozycji z katalogu napraw i dopasowana do biezacego przypadku."
        if used_market_hint and brand.lower() == "apple":
            return "Wycena zostala dopasowana do lokalnego cennika i porownana z cenami konkurencyjnych serwisow."
        if used_market_hint:
            return "Wycena zostala porownana z orientacyjnymi cenami rynkowymi."
        return "Wycena zostala przygotowana na podstawie lokalnego cennika serwisu."

    def _save_estimate(self, response, context, diagnosis, price_source, source_url, labor_minutes, google_price):
        settings_row = self.settings_service.get_or_create()
        estimate = Estimate(
            lead_id=context.lead.id if context.lead else None,
            device_id=context.device.id,
            requested_model_name=response.requested_model,
            matched_model_name=f"{context.device.brand} {context.device.model_name}",
            ai_verdict=diagnosis.technical_summary,
            damage_category=diagnosis.damage_category,
            confidence_score=diagnosis.confidence_score,
            min_price=response.price_range.min_price,
            max_price=response.price_range.max_price,
            currency=response.price_range.currency,
            is_smartphone=diagnosis.is_smartphone,
            status_code=200,
            price_source=price_source,
            hourly_rate_used=settings_row.hourly_rate,
            parts_margin_used=settings_row.parts_margin,
            tax_multiplier_used=settings_row.tax_multiplier,
            labor_minutes_used=labor_minutes,
            google_part_price=google_price,
            source_url=source_url,
        )
        self.db.add(estimate)
        if context.lead:
            from app.models import LeadStatus

            if context.lead.customer_name and context.lead.phone:
                context.lead.status = LeadStatus.READY_FOR_CONTACT
            else:
                context.lead.status = LeadStatus.ESTIMATED
        self.db.commit()
