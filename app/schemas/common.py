from pydantic import BaseModel, ConfigDict


class ORMBaseSchema(BaseModel):
    """Базовая схема с поддержкой чтения ORM-объектов."""

    model_config = ConfigDict(from_attributes=True)
