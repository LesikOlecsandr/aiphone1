from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.device import DeviceRead
from app.schemas.vision import VisionResult


class PriceRange(BaseModel):
    """Схема ценовой вилки по ремонту."""

    min_price: float = Field(ge=0)
    max_price: float = Field(ge=0)
    currency: str = Field(default="PLN", min_length=3, max_length=8)
    min_quality_tier: str
    max_quality_tier: str


class EstimateResponse(BaseModel):
    """Ответ API с результатом анализа изображения и расчётом ремонта."""

    requested_model: str
    matched_device: DeviceRead
    vision_result: VisionResult
    price_range: PriceRange
    recommended_price: float = Field(ge=0)
    markup_factor: float = Field(gt=0)
    price_source: str = "database"
    source_url: str | None = None
    labor_minutes_used: float | None = None
    customer_message: str | None = None


class EstimateLogRead(BaseModel):
    """Схема для чтения сохранённой оценки из журнала."""

    id: int
    created_at: datetime
    requested_model_name: str
    matched_model_name: str | None
    ai_verdict: str
    damage_category: str
    confidence_score: float
    min_price: float | None
    max_price: float | None
    currency: str
    is_smartphone: bool
    status_code: int
