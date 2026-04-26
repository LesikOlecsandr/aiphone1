from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import LeadStatus


class Lead(Base):
    """Заявка клиента, созданная через чат-виджет."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    problem_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_model_raw: Mapped[str | None] = mapped_column(String(128), nullable=True)
    matched_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="widget", nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    device = relationship("Device")
    messages = relationship("LeadMessage", back_populates="lead", cascade="all, delete-orphan")
    media_assets = relationship("MediaAsset", back_populates="lead", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="lead")
