from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Device, Lead, LeadMessage, LeadStatus, MediaAsset, MediaKind, MessageRole
from app.schemas.chat import LeadDetailResponse, LeadRead, MediaAssetRead, UploadResponse
from app.services.consultant_service import ConsultantService
from app.services.device_matcher import DeviceMatcherService


class LeadService:
    """Сервис лидов, чата и загрузки медиафайлов."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.upload_root = Path(settings.upload_dir)
        self.upload_root.mkdir(parents=True, exist_ok=True)

    def start_chat(self) -> tuple[Lead, str]:
        """Создаёт новую заявку и стартовое сообщение на польском языке."""

        lead = Lead(status=LeadStatus.NEW, source="widget", last_message_at=datetime.utcnow())
        self.db.add(lead)
        self.db.flush()
        greeting = "Cześć! W czym mogę pomóc Twojemu urządzeniu?"
        self._add_message(lead.id, MessageRole.ASSISTANT, greeting)
        self.db.commit()
        self.db.refresh(lead)
        return lead, greeting

    def append_user_message(
        self,
        lead_id: int,
        text: str,
        customer_name: str | None = None,
        phone: str | None = None,
        device_model: str | None = None,
    ) -> Lead:
        """Сохраняет сообщение клиента и возвращает следующий ответ ассистента."""

        lead = self._get_lead(lead_id)
        if customer_name:
            lead.customer_name = customer_name
        if phone:
            lead.phone = phone
        if device_model:
            lead.device_model_raw = device_model
            matched = DeviceMatcherService(self.db).find_best_match(device_model)
            if matched:
                lead.matched_device_id = matched.id
        if text.strip() and (lead.problem_summary is None or len(text.strip()) > len(lead.problem_summary or "")):
            lead.problem_summary = text.strip()
        if lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.IN_PROGRESS
        lead.last_message_at = datetime.utcnow()
        self._add_message(lead.id, MessageRole.USER, text)

        reply = ConsultantService(self.db).build_reply(lead, text)
        if lead.customer_name and lead.phone:
            lead.status = LeadStatus.READY_FOR_CONTACT
        self._add_message(lead.id, MessageRole.ASSISTANT, reply)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    async def save_upload(self, lead_id: int, file: UploadFile) -> UploadResponse:
        """Сохраняет загруженное изображение или видео в файловую систему."""

        lead = self._get_lead(lead_id)
        suffix = Path(file.filename or "").suffix or ".bin"
        mime = file.content_type or "application/octet-stream"
        kind = MediaKind.VIDEO if mime.startswith("video/") else MediaKind.IMAGE
        if kind == MediaKind.VIDEO:
            assistant_message = "Wideo zapisane. Teraz mogę przejrzeć objawy i przygotować warianty naprawy albo orientacyjną wycenę."
        else:
            assistant_message = "Zdjęcie zapisane. Teraz mogę omówić możliwe warianty naprawy albo przygotować orientacyjną wycenę."

        safe_name = f"{uuid4().hex}{suffix}"
        target_dir = self.upload_root / str(lead.id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
        content = await file.read()
        target_path.write_bytes(content)

        public_url = f"/uploads/{lead.id}/{safe_name}"
        asset = MediaAsset(
            lead_id=lead.id,
            kind=kind,
            file_name=file.filename or safe_name,
            mime_type=mime,
            storage_path=str(target_path),
            public_url=public_url,
            duration_seconds=None,
        )
        self.db.add(asset)
        self._add_message(lead.id, MessageRole.SYSTEM, f"Zalaczono plik: {asset.file_name}")
        self._add_message(lead.id, MessageRole.ASSISTANT, assistant_message)
        if lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.IN_PROGRESS
        lead.last_message_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(asset)
        return UploadResponse(
            media_asset=MediaAssetRead(
                id=asset.id,
                kind=asset.kind.value,
                file_name=asset.file_name,
                mime_type=asset.mime_type,
                public_url=asset.public_url,
                duration_seconds=asset.duration_seconds,
            ),
            assistant_message=assistant_message,
        )

    def list_leads(self) -> list[LeadRead]:
        """Возвращает польский список заявок для админки."""

        leads = self.db.query(Lead).order_by(Lead.created_at.desc()).all()
        return [
            LeadRead(
                id=lead.id,
                created_at=lead.created_at,
                updated_at=lead.updated_at,
                customer_name=lead.customer_name,
                phone=lead.phone,
                problem_summary=lead.problem_summary,
                device_model_raw=lead.device_model_raw,
                status=lead.status.value,
            )
            for lead in leads
        ]

    def get_detail(self, lead_id: int) -> LeadDetailResponse:
        """Возвращает детальную заявку с историей сообщений и медиа."""

        lead = self._get_lead(lead_id)
        matched_device = self.db.query(Device).filter(Device.id == lead.matched_device_id).one_or_none()
        return LeadDetailResponse(
            lead=LeadRead(
                id=lead.id,
                created_at=lead.created_at,
                updated_at=lead.updated_at,
                customer_name=lead.customer_name,
                phone=lead.phone,
                problem_summary=lead.problem_summary,
                device_model_raw=lead.device_model_raw,
                status=lead.status.value,
            ),
            matched_device=matched_device,
            messages=[
                {
                    "role": item.role.value,
                    "message_text": item.message_text,
                    "created_at": item.created_at,
                }
                for item in lead.messages
            ],
            media_assets=[
                MediaAssetRead(
                    id=item.id,
                    kind=item.kind.value,
                    file_name=item.file_name,
                    mime_type=item.mime_type,
                    public_url=item.public_url,
                    duration_seconds=item.duration_seconds,
                )
                for item in lead.media_assets
            ],
        )

    def _get_lead(self, lead_id: int) -> Lead:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).one_or_none()
        if lead is None:
            raise ValueError("Nie znaleziono zgloszenia.")
        return lead

    def _add_message(self, lead_id: int, role: MessageRole, message_text: str) -> None:
        self.db.add(LeadMessage(lead_id=lead_id, role=role, message_text=message_text))

    def update_lead_snapshot(
        self,
        lead_id: int,
        *,
        customer_name: str | None = None,
        phone: str | None = None,
        device_model: str | None = None,
        problem_summary: str | None = None,
    ) -> None:
        """Aktualizuje kluczowe dane leada po analizie lub dodatkowym dopasowaniu."""

        lead = self._get_lead(lead_id)
        if customer_name:
            lead.customer_name = customer_name
        if phone:
            lead.phone = phone
        if device_model:
            lead.device_model_raw = device_model
            matched = DeviceMatcherService(self.db).find_best_match(device_model)
            if matched:
                lead.matched_device_id = matched.id
        if problem_summary and (lead.problem_summary is None or len(problem_summary) > len(lead.problem_summary or "")):
            lead.problem_summary = problem_summary
        if lead.customer_name and lead.phone:
            lead.status = LeadStatus.READY_FOR_CONTACT
        elif lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.IN_PROGRESS
        lead.last_message_at = datetime.utcnow()
        self.db.commit()
