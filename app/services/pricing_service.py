from sqlalchemy.orm import Session

from app.models import Device, PartsPrice, ServiceLabor
from app.schemas.pricing import BulkPriceUpdateRequest, BulkPriceUpdateResponse


class PricingService:
    """Сервис массовой загрузки и обновления прайс-листа."""

    def __init__(self, db: Session) -> None:
        """Сохраняет сессию БД для дальнейших операций обновления."""

        self.db = db

    def bulk_upsert(self, payload: BulkPriceUpdateRequest) -> BulkPriceUpdateResponse:
        """Обновляет устройства, цены закупки и стоимость работ в одном запросе."""

        device_cache: dict[tuple[str, str], Device] = {}
        processed_parts = 0

        for item in payload.parts_prices:
            key = (item.brand.lower().strip(), item.model_name.lower().strip())
            device = device_cache.get(key)
            if device is None:
                device = (
                    self.db.query(Device)
                    .filter(
                        Device.brand == item.brand.strip(),
                        Device.model_name == item.model_name.strip(),
                    )
                    .one_or_none()
                )
                if device is None:
                    device = Device(
                        brand=item.brand.strip(),
                        model_name=item.model_name.strip(),
                        complexity_multiplier=item.complexity_multiplier,
                    )
                    self.db.add(device)
                    self.db.flush()
                else:
                    device.complexity_multiplier = item.complexity_multiplier
                device_cache[key] = device

            part_price = (
                self.db.query(PartsPrice)
                .filter(
                    PartsPrice.device_id == device.id,
                    PartsPrice.part_type == item.part_type,
                    PartsPrice.quality_tier == item.quality_tier,
                )
                .one_or_none()
            )
            if part_price is None:
                part_price = PartsPrice(
                    device_id=device.id,
                    part_type=item.part_type,
                    quality_tier=item.quality_tier,
                    purchase_price=item.purchase_price,
                    currency=item.currency,
                )
                self.db.add(part_price)
            else:
                part_price.purchase_price = item.purchase_price
                part_price.currency = item.currency
            processed_parts += 1

        labor_processed = 0
        for item in payload.service_labor:
            labor = (
                self.db.query(ServiceLabor)
                .filter(ServiceLabor.part_type == item.part_type)
                .one_or_none()
            )
            if labor is None:
                labor = ServiceLabor(
                    part_type=item.part_type,
                    base_labor_cost=item.base_labor_cost,
                    currency=item.currency,
                )
                self.db.add(labor)
            else:
                labor.base_labor_cost = item.base_labor_cost
                labor.currency = item.currency
            labor_processed += 1

        self.db.commit()
        return BulkPriceUpdateResponse(
            devices_processed=len(device_cache),
            parts_prices_processed=processed_parts,
            labor_rows_processed=labor_processed,
        )
