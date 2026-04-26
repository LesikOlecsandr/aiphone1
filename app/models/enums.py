from enum import StrEnum


class PartType(StrEnum):
    """Поддерживаемые типы деталей и направлений ремонта."""

    SCREEN = "screen"
    GLASS_ONLY = "glass_only"
    BODY = "body"
    BATTERY = "battery"


class QualityTier(StrEnum):
    """Категории качества устанавливаемых запчастей."""

    ORIGINAL = "original"
    COPY = "copy"
    REFURBISHED = "refurbished"


class LeadStatus(StrEnum):
    """Статусы клиентских заявок."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    READY_FOR_CONTACT = "gotowy_do_kontaktu"
    ESTIMATED = "estimated"
    CLOSED = "closed"


class MessageRole(StrEnum):
    """Роли сообщений в истории чата."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MediaKind(StrEnum):
    """Типы медиафайлов клиента."""

    IMAGE = "image"
    VIDEO = "video"


class PriceSource(StrEnum):
    """Источник цены для расчёта ремонта."""

    DATABASE = "database"
    GOOGLE_SEARCH = "google_search"
