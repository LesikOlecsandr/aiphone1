from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Device(Base):
    """Справочник поддерживаемых устройств."""

    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("brand", "model_name", name="uq_device_brand_model"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    complexity_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    parts_prices = relationship(
        "PartsPrice",
        back_populates="device",
        cascade="all, delete-orphan",
    )
    estimates = relationship("Estimate", back_populates="device")
