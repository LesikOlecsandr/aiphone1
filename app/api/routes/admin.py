from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_auth
from app.db.database import get_db
from app.schemas.pricing import BulkPriceUpdateRequest, BulkPriceUpdateResponse
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_auth)])


@router.post("/update-prices", response_model=BulkPriceUpdateResponse)
def update_prices(
    payload: BulkPriceUpdateRequest,
    db: Session = Depends(get_db),
) -> BulkPriceUpdateResponse:
    """Обновляет прайс-лист запчастей и стоимость работ пакетным запросом."""

    service = PricingService(db)
    return service.bulk_upsert(payload)
