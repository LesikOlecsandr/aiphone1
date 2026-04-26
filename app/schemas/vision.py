from pydantic import BaseModel, Field, field_validator

from app.models.enums import PartType


class VisionResult(BaseModel):
    """Строго валидированный ответ от Vision-сервиса."""

    is_smartphone: bool
    damage_category: PartType | str
    confidence_score: float = Field(ge=0.0, le=1.0)
    technical_summary: str = Field(min_length=3, max_length=1000)

    @field_validator("damage_category")
    @classmethod
    def normalize_damage_category(cls, value: PartType | str) -> str:
        """Нормализует категорию повреждения к строковому значению для унификации расчётов."""

        if isinstance(value, PartType):
            return value.value
        allowed = {item.value for item in PartType} | {"unknown"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"Unsupported damage category: {value}")
        return normalized
