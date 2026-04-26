from thefuzz import fuzz, process
from sqlalchemy.orm import Session

from app.models import Device


class DeviceMatcherService:
    """Сервис нечеткого сопоставления пользовательского ввода с моделью устройства."""

    def __init__(self, db: Session) -> None:
        """Сохраняет сессию БД для поиска устройств."""

        self.db = db

    def find_best_match(self, raw_model_name: str, score_cutoff: int = 70) -> Device | None:
        """Подбирает наиболее подходящую модель устройства по строке пользователя."""

        devices = self.db.query(Device).order_by(Device.brand, Device.model_name).all()
        if not devices:
            return None

        variants = {f"{device.brand} {device.model_name}": device for device in devices}
        match = process.extractOne(
            query=raw_model_name,
            choices=list(variants.keys()),
            scorer=fuzz.token_sort_ratio,
            score_cutoff=score_cutoff,
        )
        if not match:
            return None
        return variants[match[0]]
