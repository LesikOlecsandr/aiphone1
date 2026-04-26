from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Device
from app.schemas.device import DeviceRead
from app.schemas.parts import PartsCatalogResponse

router = APIRouter(tags=["parts"])


@router.get("/parts", response_model=PartsCatalogResponse)
def get_supported_models(
    request: Request,
    db: Session = Depends(get_db),
) -> PartsCatalogResponse:
    """Возвращает список поддерживаемых моделей для выпадающего списка виджета."""

    print(f"[REQUEST] GET /parts from {request.client.host if request.client else 'unknown'}")
    devices = db.query(Device).order_by(Device.brand, Device.model_name).all()
    return PartsCatalogResponse(
        items=[DeviceRead.model_validate(device) for device in devices],
        total=len(devices),
    )
