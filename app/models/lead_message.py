from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import MessageRole


class LeadMessage(Base):
    """Сообщение в истории диалога между клиентом и AI-консультантом."""

    __tablename__ = "lead_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    lead = relationship("Lead", back_populates="messages")
