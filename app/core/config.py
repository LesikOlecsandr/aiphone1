from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Централизованные настройки приложения."""

    app_name: str = "AI-Repair Estimator API"
    app_version: str = "0.1.0"
    database_url: str = Field(
        default="sqlite:///./repair_estimator.db",
        description="Строка подключения к базе данных.",
    )
    google_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        description="API-ключ Google AI Studio для Gemini.",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Имя модели Gemini для анализа изображений.",
    )
    default_markup_factor: float = Field(
        default=2.2,
        description="Базовый множитель наценки для расчёта стоимости.",
    )
    cors_allow_origins: list[str] = Field(
        default=["*"],
        description="Список доменов, которым разрешён доступ к API.",
    )
    upload_dir: str = Field(
        default="uploads",
        description="Каталог для хранения загруженных изображений и видео.",
    )
    default_hourly_rate: float = Field(
        default=160.0,
        description="Domyślna stawka godzinowa serwisu w PLN.",
    )
    default_parts_margin: float = Field(
        default=1.25,
        description="Domyślna marża na częściach.",
    )
    default_tax_multiplier: float = Field(
        default=1.23,
        description="Mnożnik VAT, np. 1.23 dla 23%.",
    )
    max_video_seconds: int = Field(
        default=15,
        description="Maksymalny czas video w sekundach.",
    )
    runtime_config_path: str = Field(
        default="instance/runtime_config.json",
        description="Sciezka do lokalnego pliku z techniczna konfiguracja panelu.",
    )
    admin_session_cookie_name: str = Field(
        default="ai_repair_admin_session",
        description="Nazwa ciasteczka sesji dla panelu administracyjnego.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
