from thefuzz import fuzz
from sqlalchemy.orm import Session

from app.models import RepairCatalogItem
from app.schemas.repair_catalog import RepairCatalogCreate, RepairCatalogRead


class RepairCatalogService:
    """Obsluguje katalog napraw i dopasowanie do rozmowy klienta."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_items(self) -> list[RepairCatalogRead]:
        """Zwraca wszystkie pozycje katalogu napraw."""

        items = self.db.query(RepairCatalogItem).order_by(RepairCatalogItem.created_at.desc()).all()
        return [
            RepairCatalogRead(
                id=item.id,
                title=item.title,
                base_price=item.base_price,
                description=item.description,
                category=item.category,
                created_at=item.created_at,
            )
            for item in items
        ]

    def create_item(self, payload: RepairCatalogCreate) -> RepairCatalogRead:
        """Dodaje nowa naprawe z tekstowym tytulem i cena."""

        item = RepairCatalogItem(
            title=payload.title.strip(),
            base_price=payload.base_price,
            description=(payload.description or "").strip() or None,
            category=(payload.category or "").strip() or None,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return RepairCatalogRead(
            id=item.id,
            title=item.title,
            base_price=item.base_price,
            description=item.description,
            category=item.category,
            created_at=item.created_at,
        )

    def delete_item(self, item_id: int) -> None:
        """Usuwa pozycje z katalogu napraw."""

        item = self.db.query(RepairCatalogItem).filter(RepairCatalogItem.id == item_id).one_or_none()
        if item is None:
            raise ValueError("Nie znaleziono naprawy w katalogu.")
        self.db.delete(item)
        self.db.commit()

    def find_best_matches(self, text: str, limit: int = 3, score_cutoff: int = 58) -> list[RepairCatalogItem]:
        """Dopasowuje wpis klienta do katalogu napraw po tytule i opisie."""

        haystack = self._normalize(text)
        if not haystack:
            return []

        scored: list[tuple[int, RepairCatalogItem]] = []
        for item in self.db.query(RepairCatalogItem).all():
            blob = self._normalize(" ".join(filter(None, [item.title, item.description, item.category])))
            if not blob:
                continue
            contains_bonus = 12 if blob in haystack or haystack in blob else 0
            score = max(
                fuzz.token_set_ratio(haystack, blob),
                fuzz.partial_ratio(haystack, blob),
            ) + contains_bonus
            if score >= score_cutoff:
                scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def find_strict_match(self, text: str) -> RepairCatalogItem | None:
        """Probuje znalezc bardzo bliskie dopasowanie, aby traktowac cene jako priorytet."""

        matches = self.find_best_matches(text, limit=1, score_cutoff=72)
        return matches[0] if matches else None

    @staticmethod
    def _normalize(text: str) -> str:
        """Upraszcza tekst do lepszego dopasowania pozycji katalogu."""

        value = (text or "").lower()
        replacements = {
            "pleckow": "plecow",
            "plecki": "plecow",
            "tyl": "plecy",
            "tylna": "plecy",
            "klapki": "plecy",
            "bateria": "akumulator",
            "szybka": "szklo",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        return " ".join(value.split())
