from pydantic import BaseModel

from app.schemas.device import DeviceRead


class PartsCatalogResponse(BaseModel):
    """Ответ со списком поддерживаемых устройств."""

    items: list[DeviceRead]
    total: int
