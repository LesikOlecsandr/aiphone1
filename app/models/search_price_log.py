from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SearchPriceLog(Base):
    """Лог найденных через Google Search цен и источников."""

    __tablename__ = "search_price_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    device_name: Mapped[str] = mapped_column(String(128), nullable=False)
    damage_category: Mapped[str] = mapped_column(String(32), nullable=False)
    query_text: Mapped[str] = mapped_column(String(255), nullable=False)
    price_found: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="PLN", nullable=False)
    source_domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_response_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
