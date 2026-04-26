from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import PriceSource


class Estimate(Base):
    """Лог выполненных оценок стоимости для последующей аналитики."""

    __tablename__ = "estimates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    requested_model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    matched_model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    damage_category: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="PLN", nullable=False)
    is_smartphone: Mapped[bool] = mapped_column(nullable=False, default=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    price_source: Mapped[PriceSource] = mapped_column(Enum(PriceSource), default=PriceSource.DATABASE, nullable=False)
    hourly_rate_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    parts_margin_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_multiplier_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    labor_minutes_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    google_part_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    device = relationship("Device", back_populates="estimates")
    lead = relationship("Lead", back_populates="estimates")
