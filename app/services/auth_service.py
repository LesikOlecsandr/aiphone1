import base64
import hashlib
import hmac
import secrets
import time

from app.services.runtime_config_service import RuntimeConfigService


class AuthService:
    """Obsluguje haslo administratora i podpisana sesje cookie."""

    def __init__(self) -> None:
        self.runtime = RuntimeConfigService()

    @staticmethod
    def hash_password(password: str) -> str:
        """Haszuje haslo przez PBKDF2, aby nie trzymac go jawnie."""

        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150000)
        return f"{base64.b64encode(salt).decode()}:{base64.b64encode(digest).decode()}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Sprawdza zgodnosc hasla z zapisanym hashem."""

        try:
            salt_b64, digest_b64 = stored_hash.split(":", 1)
            salt = base64.b64decode(salt_b64.encode())
            expected = base64.b64decode(digest_b64.encode())
        except Exception:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150000)
        return hmac.compare_digest(actual, expected)

    def setup_password(self, password: str) -> None:
        """Ustawia lub zmienia haslo administratora."""

        self.runtime.save({"admin_password_hash": self.hash_password(password)})

    def authenticate(self, password: str) -> bool:
        """Weryfikuje haslo na podstawie runtime config."""

        stored_hash = self.runtime.load().get("admin_password_hash") or ""
        if not stored_hash:
            return False
        return self.verify_password(password, stored_hash)

    def create_session_token(self) -> str:
        """Tworzy podpisany token sesji administratora."""

        payload = f"admin:{int(time.time()) + 60 * 60 * 12}:{secrets.token_urlsafe(12)}"
        secret = self.runtime.load()["session_secret"].encode("utf-8")
        signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(f"{payload}.{signature}".encode("utf-8")).decode("utf-8")

    def verify_session_token(self, token: str | None) -> bool:
        """Sprawdza poprawny podpis i czas waznosci tokenu sesyjnego."""

        if not token:
            return False
        try:
            decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            payload, signature = decoded.rsplit(".", 1)
            role, expires_at, _nonce = payload.split(":", 2)
        except Exception:
            return False
        if role != "admin":
            return False
        secret = self.runtime.load()["session_secret"].encode("utf-8")
        expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        return int(expires_at) > int(time.time())
