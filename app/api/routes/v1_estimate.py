from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.estimate import EstimateResponse
from app.services.estimate_service import EstimateService

router = APIRouter(prefix="/api/v1", tags=["estimate-pl"])


@router.post("/estimate", response_model=EstimateResponse)
def estimate_from_saved_media(
    payload: dict,
    db: Session = Depends(get_db),
) -> EstimateResponse:
    """Создаёт польскую оценку по уже сохранённому media asset."""

    media_asset_id = payload.get("media_asset_id")
    model_name = payload.get("device_model")
    lead_id = payload.get("lead_id")
    if not media_asset_id:
        raise HTTPException(status_code=400, detail="Brakuje danych do wyceny.")
    try:
        return EstimateService(db).create_estimate_for_media(
            lead_id=lead_id,
            media_asset_id=media_asset_id,
            model_name=model_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
