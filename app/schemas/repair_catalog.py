from datetime import datetime

from pydantic import BaseModel, Field


class RepairCatalogCreate(BaseModel):
    """Szybkie dodanie naprawy do katalogu."""

    title: str = Field(min_length=2, max_length=160)
    base_price: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=80)


class RepairCatalogRead(BaseModel):
    """Pozycja katalogu napraw do admin panelu."""

    id: int
    title: str
    base_price: float
    description: str | None = None
    category: str | None = None
    created_at: datetime
