import json
import secrets
from pathlib import Path

from app.core.config import settings


class RuntimeConfigService:
    """Czyta i zapisuje lokalna konfiguracje techniczna poza publicznym frontendem."""

    DEFAULTS = {
        "business_name": "AI Repair Estimator",
        "business_phone": "",
        "business_email": "",
        "business_address": "",
        "working_hours": "",
        "widget_title": "Wycen naprawe",
        "widget_button_label": "Wycen naprawe",
        "accent_label": "AI Konsultant",
        "gemini_model": "gemini-2.5-flash",
        "gemini_api_key": "",
        "admin_password_hash": "",
        "session_secret": "",
    }

    def __init__(self) -> None:
        self.path = Path(settings.runtime_config_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Zwraca aktualna konfiguracje, tworzac plik przy pierwszym uzyciu."""

        if not self.path.exists():
            data = dict(self.DEFAULTS)
            data["session_secret"] = secrets.token_urlsafe(48)
            self._write(data)
            return data
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}
        data = {**self.DEFAULTS, **raw}
        if not data.get("session_secret"):
            data["session_secret"] = secrets.token_urlsafe(48)
            self._write(data)
        return data

    def save(self, updates: dict) -> dict:
        """Scala i zapisuje konfiguracje na dysku."""

        current = self.load()
        current.update(updates)
        self._write(current)
        return current

    def is_setup(self) -> bool:
        """Sprawdza, czy panel ma juz ustawione haslo administratora."""

        return bool(self.load().get("admin_password_hash"))

    def get_google_api_key(self) -> str:
        """Zwraca aktywny klucz Gemini z runtime config albo fallback z env."""

        runtime_key = (self.load().get("gemini_api_key") or "").strip()
        return runtime_key or settings.google_api_key

    def get_gemini_model(self) -> str:
        """Zwraca model Gemini z runtime config albo wartosc domyslna."""

        return (self.load().get("gemini_model") or "").strip() or settings.gemini_model

    @staticmethod
    def mask_secret(value: str | None) -> str | None:
        """Maskuje sekrety do bezpiecznego podgladu w UI."""

        if not value:
            return None
        if len(value) <= 8:
            return "********"
        return f"{value[:4]}{'*' * max(len(value) - 8, 4)}{value[-4:]}"

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
