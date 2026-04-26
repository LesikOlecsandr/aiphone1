import json

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.vision import VisionResult


class VisionService:
    """Сервис анализа фото устройства через Google Gemini Vision."""

    def __init__(self) -> None:
        """Конфигурирует клиент Gemini при наличии API-ключа."""

        self.enabled = bool(settings.google_api_key)
        if self.enabled:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
        else:
            self.model = None

    def analyze_damage(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> VisionResult:
        """Отправляет изображение в Gemini и возвращает строго валидированный JSON-результат."""

        if not self.enabled or self.model is None:
            raise RuntimeError("Gemini API не настроен. Укажите GOOGLE_API_KEY в переменных окружения.")

        prompt = self._build_prompt()
        try:
            response = self.model.generate_content(
                contents=[
                    {"text": prompt},
                    {"mime_type": mime_type, "data": image_bytes},
                ],
                generation_config=GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            payload = json.loads(response.text)
            return VisionResult.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Gemini вернул JSON с некорректной структурой: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini не вернул корректный JSON-ответ.") from exc
        except Exception as exc:
            raise RuntimeError(f"Ошибка при обращении к Gemini Vision API: {exc}") from exc

    @staticmethod
    def _build_prompt() -> str:
        """Собирает мультимодальный промпт, принуждающий модель вернуть только строгий JSON."""

        return (
            "Ты работаешь как диагност для сервисного центра по ремонту смартфонов. "
            "Проанализируй изображение и верни только JSON без markdown и пояснений. "
            "Используй строго такую схему: "
            '{"is_smartphone": bool, "damage_category": "screen|glass_only|body|unknown", '
            '"confidence_score": float, "technical_summary": string}. '
            "Правила: "
            "1) is_smartphone=false, если на фото не смартфон или устройство не определяется. "
            "2) damage_category=unknown, если качество фото низкое, область поломки не видна или вывод ненадёжен. "
            "3) confidence_score от 0.0 до 1.0. "
            "4) technical_summary должен кратко описывать видимые дефекты и ограничения анализа. "
            "5) Если фото размытое, темное, обрезанное или повреждение неоднозначно, явно укажи это в technical_summary."
        )
