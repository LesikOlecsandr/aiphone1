from pydantic import BaseModel, Field

from app.models.enums import PartType, QualityTier


class PartsPriceUpsert(BaseModel):
    """Элемент обновления прайс-листа по конкретной детали."""

    brand: str = Field(min_length=2, max_length=64)
    model_name: str = Field(min_length=2, max_length=128)
    complexity_multiplier: float = Field(default=1.0, ge=0.1)
    part_type: PartType
    quality_tier: QualityTier
    purchase_price: float = Field(gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=8)


class ServiceLaborUpsert(BaseModel):
    """Элемент обновления базовой стоимости работ."""

    part_type: PartType
    base_labor_cost: float = Field(gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=8)


class BulkPriceUpdateRequest(BaseModel):
    """Пакетный запрос на обновление прайс-листа и трудозатрат."""

    parts_prices: list[PartsPriceUpsert]
    service_labor: list[ServiceLaborUpsert]


class BulkPriceUpdateResponse(BaseModel):
    """Результат пакетной загрузки прайс-листа."""

    devices_processed: int
    parts_prices_processed: int
    labor_rows_processed: int
