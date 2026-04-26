from pathlib import Path
from time import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.admin import router as legacy_admin_router
from app.api.routes.estimate import router as legacy_estimate_router
from app.api.routes.parts import router as legacy_parts_router
from app.api.routes.v1_admin import router as admin_router_v1
from app.api.routes.v1_chat import router as chat_router_v1
from app.api.routes.v1_control import router as control_router_v1
from app.api.routes.v1_estimate import router as estimate_router_v1
from app.api.routes.v1_repairs import router as repairs_router_v1
from app.core.config import settings
from app.db.database import Base, engine

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "dist"
INDEX_FILE = BASE_DIR / "index.html"
ADMIN_FILE = BASE_DIR / "admin.html"
UPLOADS_DIR = BASE_DIR / settings.upload_dir
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}


def create_application() -> FastAPI:
    """Tworzy aplikacje FastAPI dla widzetu, czatu i panelu sterowania."""

    app = FastAPI(
        title="AI-Repair Estimator API",
        version="0.3.0",
        description="Polska wersja backendu dla widzetu AI Repair Estimator i panelu technicznego.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Dodaje podstawowe naglowki bezpieczenstwa dla panelu i widzetu."""

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self' http: https:; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'self';"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.middleware("http")
    async def basic_rate_limit(request: Request, call_next):
        """Dodaje prosty rate limit dla publicznego chatu i logowania."""

        path = request.url.path
        if path.startswith("/api/v1/chat") or path.startswith("/api/v1/control/login"):
            client_ip = request.client.host if request.client else "unknown"
            now = time()
            window_seconds = 60
            limit = 18 if path.startswith("/api/v1/chat") else 8
            bucket_key = f"{client_ip}:{path.split('/', 4)[3]}"
            recent = [stamp for stamp in RATE_LIMIT_BUCKETS.get(bucket_key, []) if now - stamp < window_seconds]
            if len(recent) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Zbyt wiele prob w krotkim czasie. Sprobuj ponownie za chwile."},
                )
            recent.append(now)
            RATE_LIMIT_BUCKETS[bucket_key] = recent
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

    app.include_router(legacy_estimate_router)
    app.include_router(legacy_parts_router)
    app.include_router(legacy_admin_router)
    app.include_router(chat_router_v1)
    app.include_router(estimate_router_v1)
    app.include_router(admin_router_v1)
    app.include_router(repairs_router_v1)
    app.include_router(control_router_v1)

    @app.get("/", include_in_schema=False)
    def read_index() -> FileResponse:
        """Zwraca strone testowa z osadzonym widzetem."""

        return FileResponse(INDEX_FILE)

    @app.get("/control-center", include_in_schema=False)
    def read_control_center() -> FileResponse:
        """Zwraca glowny panel techniczny i administracyjny."""

        return FileResponse(ADMIN_FILE)

    @app.get("/admin-panel", include_in_schema=False)
    def redirect_admin_panel() -> RedirectResponse:
        """Przekierowuje stare wejscie do nowego control center."""

        return RedirectResponse(url="/control-center", status_code=302)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        """Zwraca prosty status gotowosci serwisu."""

        return {"status": "ok"}

    return app


Base.metadata.create_all(bind=engine)
app = create_application()
