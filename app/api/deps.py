from fastapi import Cookie, HTTPException, status

from app.core.config import settings
from app.services.auth_service import AuthService


def require_admin_auth(
    admin_session: str | None = Cookie(default=None, alias=settings.admin_session_cookie_name),
) -> None:
    """Blokuje dostep do panelu i API bez poprawnej sesji administratora."""

    if not AuthService().verify_session_token(admin_session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagane logowanie do panelu technicznego.",
        )
