from pydantic import Field

from app.schemas.common import ORMBaseSchema


class DeviceRead(ORMBaseSchema):
    """Схема устройства для выдачи в API."""

    id: int
    brand: str
    model_name: str
    complexity_multiplier: float = Field(ge=0.1)
