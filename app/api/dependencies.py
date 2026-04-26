from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.device_matcher import DeviceMatcherService
from app.services.price_calculator import PriceCalculator
from app.services.pricing_service import PricingService
from app.services.vision_service import VisionService


def get_device_matcher(db: Session) -> DeviceMatcherService:
    """Создаёт сервис нечеткого поиска моделей устройств."""

    return DeviceMatcherService(db)


def get_price_calculator(db: Session) -> PriceCalculator:
    """Создаёт сервис расчёта стоимости ремонта."""

    return PriceCalculator(db)


def get_pricing_service(db: Session) -> PricingService:
    """Создаёт сервис пакетного обновления прайс-листа."""

    return PricingService(db)


def get_vision_service() -> VisionService:
    """Создаёт экземпляр сервиса интеграции с Gemini Vision."""

    return VisionService()
