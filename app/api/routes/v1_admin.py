from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin_auth
from app.db.database import get_db
from app.schemas.chat import LeadDetailResponse, LeadRead
from app.schemas.pricing import BulkPriceUpdateRequest, BulkPriceUpdateResponse
from app.schemas.settings import ServiceSettingsRead, ServiceSettingsUpdate
from app.services.lead_service import LeadService
from app.services.pricing_service import PricingService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/v1/admin", tags=["admin-pl"], dependencies=[Depends(require_admin_auth)])


@router.get("/settings", response_model=ServiceSettingsRead)
def get_settings(db: Session = Depends(get_db)) -> ServiceSettingsRead:
    """Возвращает сервисные настройки для польской админки."""

    return SettingsService(db).read()


@router.put("/settings", response_model=ServiceSettingsRead)
def update_settings(payload: ServiceSettingsUpdate, db: Session = Depends(get_db)) -> ServiceSettingsRead:
    """Обновляет hourly_rate, marza и VAT."""

    return SettingsService(db).update(payload)


@router.get("/leads", response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db)) -> list[LeadRead]:
    """Возвращает список zgłoszen."""

    return LeadService(db).list_leads()


@router.get("/leads/{lead_id}", response_model=LeadDetailResponse)
def get_lead_detail(lead_id: int, db: Session = Depends(get_db)) -> LeadDetailResponse:
    """Возвращает детальную заявку с чатом и медиа."""

    try:
        return LeadService(db).get_detail(lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/update-prices", response_model=BulkPriceUpdateResponse)
def update_prices(payload: BulkPriceUpdateRequest, db: Session = Depends(get_db)) -> BulkPriceUpdateResponse:
    """Пакетно обновляет cennik и stawki robocizny."""

    return PricingService(db).bulk_upsert(payload)
