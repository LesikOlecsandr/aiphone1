from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ServiceSettings
from app.schemas.settings import ServiceSettingsRead, ServiceSettingsUpdate


class SettingsService:
    """Сервис чтения и обновления сервисных настроек."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self) -> ServiceSettings:
        """Возвращает единственную запись настроек, создавая её при первом запуске."""

        row = self.db.query(ServiceSettings).filter(ServiceSettings.id == 1).one_or_none()
        if row is None:
            row = ServiceSettings(
                id=1,
                hourly_rate=settings.default_hourly_rate,
                parts_margin=settings.default_parts_margin,
                tax_multiplier=settings.default_tax_multiplier,
                currency="PLN",
            )
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
        return row

    def read(self) -> ServiceSettingsRead:
        """Читает настройки в виде схемы API."""

        row = self.get_or_create()
        return ServiceSettingsRead(
            hourly_rate=row.hourly_rate,
            parts_margin=row.parts_margin,
            tax_multiplier=row.tax_multiplier,
            currency=row.currency,
            updated_at=row.updated_at,
        )

    def update(self, payload: ServiceSettingsUpdate) -> ServiceSettingsRead:
        """Обновляет настройки сервиса."""

        row = self.get_or_create()
        row.hourly_rate = payload.hourly_rate
        row.parts_margin = payload.parts_margin
        row.tax_multiplier = payload.tax_multiplier
        row.currency = payload.currency
        self.db.commit()
        self.db.refresh(row)
        return self.read()
