from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.models import Device, PartType, PartsPrice, QualityTier, ServiceLabor


LABOR_PRICES = {
    PartType.SCREEN: 220.0,
    PartType.GLASS_ONLY: 180.0,
    PartType.BODY: 160.0,
    PartType.BATTERY: 120.0,
}


DEVICE_SEED = [
    ("Apple", "iPhone 15 Pro", 1.45),
    ("Apple", "iPhone 15", 1.35),
    ("Apple", "iPhone 14 Pro", 1.40),
    ("Apple", "iPhone 14", 1.30),
    ("Apple", "iPhone 13 Pro", 1.32),
    ("Apple", "iPhone 13", 1.24),
    ("Samsung", "Galaxy S24 Ultra", 1.50),
    ("Samsung", "Galaxy S24", 1.38),
    ("Samsung", "Galaxy S23 Ultra", 1.42),
    ("Samsung", "Galaxy S23", 1.29),
]


PART_PRICE_MATRIX = {
    "screen": {"copy": 420.0, "refurbished": 560.0, "original": 780.0},
    "glass_only": {"copy": 250.0, "refurbished": 340.0, "original": 460.0},
    "body": {"copy": 160.0, "refurbished": 220.0, "original": 320.0},
    "battery": {"copy": 110.0, "refurbished": 145.0, "original": 210.0},
}


def seed_database() -> None:
    """Создаёт таблицы и заполняет БД тестовыми устройствами, запчастями и трудозатратами."""

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        _seed_labor(db)
        _seed_devices_and_parts(db)
        db.commit()
    finally:
        db.close()


def _seed_labor(db: Session) -> None:
    """Добавляет или обновляет базовые расценки на работы по каждому типу ремонта."""

    for part_type, base_cost in LABOR_PRICES.items():
        labor = db.query(ServiceLabor).filter(ServiceLabor.part_type == part_type).one_or_none()
        if labor is None:
            db.add(ServiceLabor(part_type=part_type, base_labor_cost=base_cost, currency="PLN"))
        else:
            labor.base_labor_cost = base_cost
            labor.currency = "PLN"


def _seed_devices_and_parts(db: Session) -> None:
    """Наполняет базу устройствами и набором тестовых цен по каждой категории качества."""

    quality_sequence = [
        QualityTier.COPY,
        QualityTier.REFURBISHED,
        QualityTier.ORIGINAL,
    ]
    multiplier_offset = {
        "Apple": 1.12,
        "Samsung": 1.08,
    }

    for brand, model_name, complexity in DEVICE_SEED:
        device = (
            db.query(Device)
            .filter(Device.brand == brand, Device.model_name == model_name)
            .one_or_none()
        )
        if device is None:
            device = Device(
                brand=brand,
                model_name=model_name,
                complexity_multiplier=complexity,
            )
            db.add(device)
            db.flush()
        else:
            device.complexity_multiplier = complexity

        brand_factor = multiplier_offset.get(brand, 1.0)
        model_factor = complexity / 1.2
        for part_type in PartType:
            base_prices = PART_PRICE_MATRIX[part_type.value]
            for quality_tier in quality_sequence:
                adjusted_price = round(base_prices[quality_tier.value] * brand_factor * model_factor, 2)
                part = (
                    db.query(PartsPrice)
                    .filter(
                        PartsPrice.device_id == device.id,
                        PartsPrice.part_type == part_type,
                        PartsPrice.quality_tier == quality_tier,
                    )
                    .one_or_none()
                )
                if part is None:
                    db.add(
                        PartsPrice(
                            device_id=device.id,
                            part_type=part_type,
                            quality_tier=quality_tier,
                            purchase_price=adjusted_price,
                            currency="PLN",
                        )
                    )
                else:
                    part.purchase_price = adjusted_price
                    part.currency = "PLN"


if __name__ == "__main__":
    seed_database()
