from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.device import DeviceRead


class ChatStartResponse(BaseModel):
    """Ответ на инициализацию польского чата."""

    lead_id: int
    message: str


class ChatMessageCreate(BaseModel):
    """Входящее текстовое сообщение клиента."""

    lead_id: int
    text: str = Field(min_length=1, max_length=4000)
    customer_name: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    device_model: str | None = Field(default=None, max_length=128)


class ChatMessageResponse(BaseModel):
    """Odpowiedź czatu wraz ze statusem leada po zapisaniu wiadomości."""

    message: str
    lead_status: str
    customer_name: str | None = None
    phone: str | None = None
    device_model: str | None = None


class ChatMessageRead(BaseModel):
    """Сообщение из истории чата."""

    role: str
    message_text: str
    created_at: datetime


class MediaAssetRead(BaseModel):
    """Медиафайл, привязанный к заявке."""

    id: int
    kind: str
    file_name: str
    mime_type: str
    public_url: str
    duration_seconds: float | None = None


class LeadRead(BaseModel):
    """Заявка для списка в админке."""

    id: int
    created_at: datetime
    updated_at: datetime
    customer_name: str | None
    phone: str | None
    problem_summary: str | None
    device_model_raw: str | None
    status: str


class LeadDetailResponse(BaseModel):
    """Детальная заявка с историей чата и медиа."""

    lead: LeadRead
    matched_device: DeviceRead | None = None
    messages: list[ChatMessageRead]
    media_assets: list[MediaAssetRead]


class UploadResponse(BaseModel):
    """Ответ после сохранения изображения или видео."""

    media_asset: MediaAssetRead
    assistant_message: str
