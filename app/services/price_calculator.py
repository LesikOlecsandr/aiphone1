from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Device, PartType, PartsPrice, QualityTier, ServiceLabor
from app.schemas.estimate import PriceRange
from app.schemas.vision import VisionResult


@dataclass
class CalculationResult:
    """Внутренний контейнер итогового расчёта стоимости ремонта."""

    price_range: PriceRange
    recommended_price: float
    markup_factor: float


class PriceCalculator:
    """Калькулятор стоимости ремонта на основе диагноза Vision и прайс-листа."""

    def __init__(self, db: Session, markup_factor: float | None = None) -> None:
        """Инициализирует калькулятор с доступом к БД и параметрами наценки."""

        self.db = db
        self.markup_factor = markup_factor or settings.default_markup_factor

    def calculate(self, vision_result: VisionResult, device: Device) -> CalculationResult:
        """Считает ценовую вилку и рекомендованную цену для выбранного устройства."""

        damage_category = vision_result.damage_category
        if damage_category == "unknown":
            raise ValueError("Невозможно выполнить расчёт: категория повреждения не определена.")

        part_type = PartType(damage_category)
        labor = (
            self.db.query(ServiceLabor)
            .filter(ServiceLabor.part_type == part_type)
            .one_or_none()
        )
        if labor is None:
            raise ValueError(f"Для типа ремонта '{part_type.value}' не настроена стоимость работ.")

        prices = (
            self.db.query(PartsPrice)
            .filter(
                PartsPrice.device_id == device.id,
                PartsPrice.part_type == part_type,
            )
            .all()
        )
        if not prices:
            raise ValueError(
                f"Для модели '{device.model_name}' не найден прайс по категории '{part_type.value}'."
            )

        ranked_prices = sorted(
            prices,
            key=lambda item: self._quality_rank(item.quality_tier),
        )
        min_part = ranked_prices[0]
        max_part = ranked_prices[-1]

        min_total = self._compute_total(min_part.purchase_price, labor.base_labor_cost, device.complexity_multiplier)
        max_total = self._compute_total(max_part.purchase_price, labor.base_labor_cost, device.complexity_multiplier)
        recommended = round((min_total + max_total) / 2, 2)

        return CalculationResult(
            price_range=PriceRange(
                min_price=min_total,
                max_price=max_total,
                currency=min_part.currency,
                min_quality_tier=min_part.quality_tier.value,
                max_quality_tier=max_part.quality_tier.value,
            ),
            recommended_price=recommended,
            markup_factor=self.markup_factor,
        )

    def _compute_total(self, purchase_price: float, base_labor_cost: float, device_complexity: float) -> float:
        """Вычисляет итоговую стоимость ремонта по заданной бизнес-формуле."""

        total_price = (purchase_price * self.markup_factor) + (base_labor_cost * device_complexity)
        return round(total_price, 2)

    @staticmethod
    def _quality_rank(quality_tier: QualityTier) -> int:
        """Определяет порядок качества для построения ценовой вилки от дешёвого к дорогому."""

        ranking = {
            QualityTier.COPY: 0,
            QualityTier.REFURBISHED: 1,
            QualityTier.ORIGINAL: 2,
        }
        return ranking[quality_tier]
