from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin_auth
from app.core.config import settings
from app.db.database import get_db
from app.models import Estimate, Lead, LeadStatus, RepairCatalogItem
from app.schemas.control import (
    ControlBootstrapResponse,
    ControlConfigRead,
    ControlConfigUpdate,
    ControlLoginRequest,
    ControlSetupRequest,
    ControlStatsRead,
)
from app.services.auth_service import AuthService
from app.services.runtime_config_service import RuntimeConfigService

router = APIRouter(prefix="/api/v1/control", tags=["control-center"])


def _set_admin_cookie(response: Response, request: Request, token: str) -> None:
    """Ustawia bezpieczne cookie sesyjne dla panelu."""

    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )


@router.get("/bootstrap", response_model=ControlBootstrapResponse)
def bootstrap(request: Request) -> ControlBootstrapResponse:
    """Zwraca stan poczatkowy panelu: setup i sesje."""

    runtime = RuntimeConfigService()
    auth = AuthService()
    cookie = request.cookies.get(settings.admin_session_cookie_name)
    return ControlBootstrapResponse(
        is_setup=runtime.is_setup(),
        is_authenticated=auth.verify_session_token(cookie),
    )


@router.get("/public-config")
def get_public_config() -> dict[str, str | None]:
    """Zwraca publiczna konfiguracje potrzebna widzetowi na stronie."""

    config = RuntimeConfigService().load()
    return {
        "business_name": config["business_name"],
        "business_phone": config["business_phone"] or None,
        "business_email": config["business_email"] or None,
        "business_address": config["business_address"] or None,
        "working_hours": config["working_hours"] or None,
        "widget_title": config["widget_title"],
        "widget_button_label": config["widget_button_label"],
        "accent_label": config["accent_label"],
    }


@router.post("/setup", response_model=ControlConfigRead)
def setup_panel(payload: ControlSetupRequest, request: Request, response: Response) -> ControlConfigRead:
    """Wykonuje pierwsza konfiguracje panelu i ustawia haslo administratora."""

    runtime = RuntimeConfigService()
    auth = AuthService()
    existing_cookie = request.cookies.get(settings.admin_session_cookie_name)
    if runtime.is_setup() and not auth.verify_session_token(existing_cookie):
        raise HTTPException(status_code=403, detail="Pierwsza konfiguracja jest juz zakonczona.")
    auth.setup_password(payload.password)
    runtime.save(
        {
            "business_name": payload.business_name.strip(),
            "business_phone": (payload.business_phone or "").strip(),
            "business_email": (payload.business_email or "").strip(),
            "business_address": (payload.business_address or "").strip(),
            "working_hours": (payload.working_hours or "").strip(),
            "gemini_api_key": (payload.gemini_api_key or "").strip(),
            "gemini_model": payload.gemini_model.strip(),
        }
    )
    _set_admin_cookie(response, request, auth.create_session_token())
    config = runtime.load()
    return ControlConfigRead(
        business_name=config["business_name"],
        business_phone=config["business_phone"] or None,
        business_email=config["business_email"] or None,
        business_address=config["business_address"] or None,
        working_hours=config["working_hours"] or None,
        widget_title=config["widget_title"],
        widget_button_label=config["widget_button_label"],
        accent_label=config["accent_label"],
        gemini_model=config["gemini_model"],
        gemini_api_key_masked=runtime.mask_secret(config.get("gemini_api_key")),
        has_gemini_api_key=bool((config.get("gemini_api_key") or "").strip() or settings.google_api_key),
    )


@router.post("/login")
def login(payload: ControlLoginRequest, request: Request, response: Response) -> dict[str, bool]:
    """Loguje administratora do technicznego panelu."""

    auth = AuthService()
    if not auth.authenticate(payload.password):
        raise HTTPException(status_code=401, detail="Niepoprawne haslo administratora.")
    _set_admin_cookie(response, request, auth.create_session_token())
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    """Wylogowuje administratora i usuwa cookie sesji."""

    response.delete_cookie(settings.admin_session_cookie_name, path="/")
    return {"ok": True}


@router.get("/config", response_model=ControlConfigRead, dependencies=[Depends(require_admin_auth)])
def get_config() -> ControlConfigRead:
    """Zwraca techniczna i publiczna konfiguracje serwisu."""

    runtime = RuntimeConfigService()
    config = runtime.load()
    return ControlConfigRead(
        business_name=config["business_name"],
        business_phone=config["business_phone"] or None,
        business_email=config["business_email"] or None,
        business_address=config["business_address"] or None,
        working_hours=config["working_hours"] or None,
        widget_title=config["widget_title"],
        widget_button_label=config["widget_button_label"],
        accent_label=config["accent_label"],
        gemini_model=config["gemini_model"],
        gemini_api_key_masked=runtime.mask_secret(config.get("gemini_api_key")),
        has_gemini_api_key=bool((config.get("gemini_api_key") or "").strip() or settings.google_api_key),
    )


@router.put("/config", response_model=ControlConfigRead, dependencies=[Depends(require_admin_auth)])
def update_config(payload: ControlConfigUpdate) -> ControlConfigRead:
    """Aktualizuje dane kontaktowe, widget i sekrety serwisu."""

    runtime = RuntimeConfigService()
    updates = {
        "business_name": payload.business_name.strip(),
        "business_phone": (payload.business_phone or "").strip(),
        "business_email": (payload.business_email or "").strip(),
        "business_address": (payload.business_address or "").strip(),
        "working_hours": (payload.working_hours or "").strip(),
        "widget_title": payload.widget_title.strip(),
        "widget_button_label": payload.widget_button_label.strip(),
        "accent_label": payload.accent_label.strip(),
        "gemini_model": payload.gemini_model.strip(),
    }
    if payload.gemini_api_key is not None:
        updates["gemini_api_key"] = payload.gemini_api_key.strip()
    if payload.new_admin_password:
        AuthService().setup_password(payload.new_admin_password)
    config = runtime.save(updates)
    return ControlConfigRead(
        business_name=config["business_name"],
        business_phone=config["business_phone"] or None,
        business_email=config["business_email"] or None,
        business_address=config["business_address"] or None,
        working_hours=config["working_hours"] or None,
        widget_title=config["widget_title"],
        widget_button_label=config["widget_button_label"],
        accent_label=config["accent_label"],
        gemini_model=config["gemini_model"],
        gemini_api_key_masked=runtime.mask_secret(config.get("gemini_api_key")),
        has_gemini_api_key=bool((config.get("gemini_api_key") or "").strip() or settings.google_api_key),
    )


@router.get("/stats", response_model=ControlStatsRead, dependencies=[Depends(require_admin_auth)])
def get_stats(db: Session = Depends(get_db)) -> ControlStatsRead:
    """Zwraca proste statystyki potrzebne w panelu."""

    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    estimated_leads = db.query(func.count(Lead.id)).filter(Lead.status == LeadStatus.ESTIMATED).scalar() or 0
    total_estimates = db.query(func.count(Estimate.id)).scalar() or 0
    average_estimate_value = (
        db.query(func.avg((Estimate.min_price + Estimate.max_price) / 2)).scalar() or 0.0
    )
    repair_catalog_size = db.query(func.count(RepairCatalogItem.id)).scalar() or 0
    return ControlStatsRead(
        total_leads=int(total_leads),
        estimated_leads=int(estimated_leads),
        total_estimates=int(total_estimates),
        average_estimate_value=round(float(average_estimate_value), 2),
        repair_catalog_size=int(repair_catalog_size),
    )
