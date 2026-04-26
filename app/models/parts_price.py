from sqlalchemy import Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import PartType, QualityTier


class PartsPrice(Base):
    """Цены закупки запчастей для конкретной модели устройства."""

    __tablename__ = "parts_prices"
    __table_args__ = (
        UniqueConstraint("device_id", "part_type", "quality_tier", name="uq_device_part_quality"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    part_type: Mapped[PartType] = mapped_column(Enum(PartType), nullable=False)
    quality_tier: Mapped[QualityTier] = mapped_column(Enum(QualityTier), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="PLN", nullable=False)

    device = relationship("Device", back_populates="parts_prices")
