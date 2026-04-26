from datetime import datetime

from pydantic import BaseModel, Field


class ServiceSettingsRead(BaseModel):
    """Текущие настройки сервиса для польской админки."""

    hourly_rate: float = Field(gt=0)
    parts_margin: float = Field(gt=0)
    tax_multiplier: float = Field(gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=8)
    updated_at: datetime | None = None


class ServiceSettingsUpdate(BaseModel):
    """Изменение настроек расчёта."""

    hourly_rate: float = Field(gt=0)
    parts_margin: float = Field(gt=0)
    tax_multiplier: float = Field(gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=8)
