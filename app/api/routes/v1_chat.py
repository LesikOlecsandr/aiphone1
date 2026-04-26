from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatStartResponse, LeadDetailResponse, LeadRead, UploadResponse
from app.services.lead_service import LeadService

router = APIRouter(prefix="/api/v1/chat", tags=["chat-pl"])


@router.post("/start", response_model=ChatStartResponse)
def start_chat(db: Session = Depends(get_db)) -> ChatStartResponse:
    """Стартует польский чат и возвращает первое сообщение."""

    lead, message = LeadService(db).start_chat()
    return ChatStartResponse(lead_id=lead.id, message=message)


@router.post("/message", response_model=ChatMessageResponse)
def send_message(payload: ChatMessageCreate, db: Session = Depends(get_db)) -> ChatMessageResponse:
    """Принимает текст клиента и возвращает следующий ответ ассистента."""

    try:
        lead = LeadService(db).append_user_message(
            lead_id=payload.lead_id,
            text=payload.text,
            customer_name=payload.customer_name,
            phone=payload.phone,
            device_model=payload.device_model,
        )
        last_assistant = next((item for item in reversed(lead.messages) if item.role.value == "assistant"), None)
        return ChatMessageResponse(
            message=last_assistant.message_text if last_assistant else "",
            lead_status=lead.status.value,
            customer_name=lead.customer_name,
            phone=lead.phone,
            device_model=lead.device_model_raw,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/upload", response_model=UploadResponse)
async def upload_media(
    lead_id: int = Form(...),
    media: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    """Сохраняет obraz или video, привязанное к заявке."""

    try:
        return await LeadService(db).save_upload(lead_id=lead_id, file=media)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
