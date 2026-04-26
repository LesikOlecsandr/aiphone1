from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin_auth
from app.db.database import get_db
from app.schemas.repair_catalog import RepairCatalogCreate, RepairCatalogRead
from app.services.repair_catalog_service import RepairCatalogService

router = APIRouter(prefix="/api/v1/admin/repairs", tags=["repairs-pl"], dependencies=[Depends(require_admin_auth)])


@router.get("", response_model=list[RepairCatalogRead])
def list_repairs(db: Session = Depends(get_db)) -> list[RepairCatalogRead]:
    """Zwraca katalog napraw dla admin panelu."""

    return RepairCatalogService(db).list_items()


@router.post("", response_model=RepairCatalogRead)
def create_repair(payload: RepairCatalogCreate, db: Session = Depends(get_db)) -> RepairCatalogRead:
    """Dodaje nowa pozycje typu 'reinstalacja Windows - 150 PLN'."""

    return RepairCatalogService(db).create_item(payload)


@router.delete("/{item_id}")
def delete_repair(item_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Usuwa pozycje z katalogu napraw."""

    try:
        RepairCatalogService(db).delete_item(item_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
