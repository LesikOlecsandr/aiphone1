import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from app.models import Device, PartType, SearchPriceLog
from app.services.runtime_config_service import RuntimeConfigService


class PolishVisionResult(BaseModel):
    """Строгий польский результат диагностики устройства."""

    is_smartphone: bool
    damage_category: str = Field(pattern="^(screen|glass_only|body|battery|unknown)$")
    confidence_score: float = Field(ge=0, le=1)
    technical_summary: str


@dataclass
class GoogleSearchPriceResult:
    """Результат поискового фолбэка по цене детали."""

    part_price: float
    source_url: str | None
    source_domain: str | None
    summary: str


@dataclass
class GoogleSearchRepairResult:
    """Результат поиска ориентировочной рыночной цены готового ремонта."""

    repair_price: float
    source_url: str | None
    source_domain: str | None
    summary: str


class PolishGeminiService:
    """Польский сервис диагностики и поиска цены через Gemini 2.5 Flash."""

    def __init__(self) -> None:
        runtime = RuntimeConfigService()
        self.api_key = runtime.get_google_api_key()
        self.model_name = runtime.get_gemini_model()

    def _get_client_and_types(self):
        if not self.api_key:
            raise RuntimeError("Brak klucza Gemini API.")
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        return client, types

    def analyze_media(self, media_path: str, mime_type: str) -> PolishVisionResult:
        """Анализирует obraz или video и возвращает польский JSON-диагноз."""

        client, types = self._get_client_and_types()
        path = Path(media_path)
        prompt = (
            "Jestes ekspertem serwisu Apple/Samsung. Rozmawiaj po polsku, badz uprzejmy i profesjonalny. "
            "Przeanalizuj zalaczone media i zwroc wyłącznie JSON bez markdown. "
            'Schema: {"is_smartphone": bool, "damage_category": "screen|glass_only|body|battery|unknown", '
            '"confidence_score": float, "technical_summary": string}. '
            "Jesli to nie jest smartfon, ustaw is_smartphone=false. "
            "Jesli jakosc jest zbyt niska lub uszkodzenie niejednoznaczne, ustaw damage_category=unknown. "
            "Opis techniczny ma byc po polsku."
        )

        uploaded_file = None
        if mime_type.startswith("video/") or path.stat().st_size > 20 * 1024 * 1024:
            uploaded_file = client.files.upload(file=path)
            contents = [uploaded_file, prompt]
        else:
            inline_bytes = path.read_bytes()
            contents = [
                types.Part.from_bytes(data=inline_bytes, mime_type=mime_type),
                prompt,
            ]

        response = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        payload = json.loads(response.text)
        return PolishVisionResult.model_validate(payload)

    def search_part_price(
        self,
        device: Device,
        part_type: PartType,
        db,
    ) -> GoogleSearchPriceResult:
        """Использует Grounding with Google Search для поиска актуальной цены детали в PLN."""

        client, types = self._get_client_and_types()
        query = (
            f"Znajdz aktualna cene czesci {part_type.value} do {device.brand} {device.model_name} "
            "w PLN na polskich stronach, preferuj Allegro, Ceneo, sklepy GSM i hurtownie."
        )
        prompt = (
            "Jestes ekspertem serwisu Apple/Samsung. Rozmawiaj po polsku, badz uprzejmy i profesjonalny. "
            "Wyszukaj aktualna orientacyjna cene czesci w PLN na polskich stronach. "
            "Zwroc wyłącznie JSON o schemacie: "
            '{"part_price": number, "source_url": string, "source_domain": string, "summary": string}. '
            f"Dane: {query}"
        )
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )

        payload = json.loads(response.text)
        result = GoogleSearchPriceResult(
            part_price=float(payload["part_price"]),
            source_url=payload.get("source_url"),
            source_domain=payload.get("source_domain"),
            summary=payload.get("summary", ""),
        )
        db.add(
            SearchPriceLog(
                device_name=f"{device.brand} {device.model_name}",
                damage_category=part_type.value,
                query_text=query,
                price_found=result.part_price,
                currency="PLN",
                source_domain=result.source_domain,
                source_url=result.source_url,
                raw_response_excerpt=result.summary[:1500],
            )
        )
        db.commit()
        return result

    def search_competitor_repair_price(
        self,
        device: Device,
        part_type: PartType,
        db,
    ) -> GoogleSearchRepairResult:
        """Szuka rynkowej ceny gotowej uslugi naprawy, preferujac polskich konkurentow."""

        client, types = self._get_client_and_types()
        preferred_domain = "iflix"
        query = (
            f"Znajdz aktualna cene uslugi naprawy {part_type.value} dla {device.brand} {device.model_name} "
            "w PLN na polskich stronach serwisow. Preferuj strony konkurencji, szczegolnie iflix, "
            "a potem inne serwisy GSM, cenniki lokalne i porownywarki."
        )
        prompt = (
            "Jestes ekspertem serwisu Apple/Samsung. Rozmawiaj po polsku, badz uprzejmy i profesjonalny. "
            "Wyszukaj orientacyjna cene gotowej uslugi naprawy w PLN na polskich stronach. "
            "Najpierw sprawdz konkurencyjne serwisy i cenniki napraw, a dopiero potem ogolne wyniki. "
            f"Jesli urzadzenie jest Apple, w pierwszej kolejnosci szukaj wynikow powiazanych z {preferred_domain}. "
            "Jesli znajdziesz kilka cen, wybierz najbardziej realistyczna i konkurencyjna, bliska dolnej lub srodkowej czesci rynku, a nie najwyzsza. "
            "W pierwszej kolejnosci bierz ceny z iflix, a jesli ich brak, wtedy z innych polskich serwisow. "
            "Nie szukaj samej czesci, tylko ceny kompletnej uslugi wymiany lub naprawy. "
            "Zwroc wylacznie JSON o schemacie: "
            '{"repair_price": number, "source_url": string, "source_domain": string, "summary": string}. '
            f"Dane: {query}"
        )
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0.15,
                response_mime_type="application/json",
            ),
        )
        payload = json.loads(response.text)
        result = GoogleSearchRepairResult(
            repair_price=float(payload["repair_price"]),
            source_url=payload.get("source_url"),
            source_domain=payload.get("source_domain"),
            summary=payload.get("summary", ""),
        )
        db.add(
            SearchPriceLog(
                device_name=f"{device.brand} {device.model_name}",
                damage_category=f"{part_type.value}_repair_market",
                query_text=query,
                price_found=result.repair_price,
                currency="PLN",
                source_domain=result.source_domain,
                source_url=result.source_url,
                raw_response_excerpt=result.summary[:1500],
            )
        )
        db.commit()
        return result
