from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ServiceSettings(Base):
    """Глобальные настройки сервиса для польской версии калькулятора."""

    __tablename__ = "service_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    parts_margin: Mapped[float] = mapped_column(Float, nullable=False)
    tax_multiplier: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="PLN", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
