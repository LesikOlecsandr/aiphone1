from sqlalchemy import Enum, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.enums import PartType


class ServiceLabor(Base):
    """Глобальный справочник базовой стоимости работ по типу ремонта."""

    __tablename__ = "service_labor"
    __table_args__ = (
        UniqueConstraint("part_type", name="uq_service_labor_part_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    part_type: Mapped[PartType] = mapped_column(Enum(PartType), nullable=False)
    base_labor_cost: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="PLN", nullable=False)
