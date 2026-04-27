import re

from app.services.device_matcher import DeviceMatcherService
from app.services.repair_catalog_service import RepairCatalogService
from app.services.runtime_config_service import RuntimeConfigService


class ConsultantService:
    """Konsultant sprzedazowy, ktory rozmawia naturalnie, wyjasnia roznice i prowadzi do leada."""

    def __init__(self, db) -> None:
        self.db = db
        self.catalog = RepairCatalogService(db)
        self.matcher = DeviceMatcherService(db)
        self.runtime = RuntimeConfigService()

    def build_reply(self, lead, user_text: str) -> str:
        """Buduje odpowiedz konsultanta na podstawie kontekstu, katalogu i intencji klienta."""

        user_text = (user_text or "").strip()
        self._update_lead_snapshot_from_text(lead, user_text)

        closing_reply = self._try_build_closing_reply(lead, user_text)
        if closing_reply:
            return closing_reply

        history_text = self._history_context(lead)
        topic = self._detect_topic(f"{history_text} {user_text}")
        catalog_query = " ".join(filter(None, [lead.device_model_raw, topic, history_text, user_text]))
        catalog_matches = self.catalog.find_best_matches(catalog_query, limit=5)
        strict_match = self.catalog.find_strict_match(catalog_query)
        if strict_match and all(item.id != strict_match.id for item in catalog_matches):
            catalog_matches = [strict_match, *catalog_matches][:5]
        variant_matches = self._find_variant_matches(catalog_matches)

        if not lead.device_model_raw and topic != "unknown":
            return (
                "Jasne, pomoge. Napisz prosze dokladny model urzadzenia, a od razu porownam dostepne warianty naprawy, "
                "wyjasnie roznice i podpowiem, co bedzie najbardziej oplacalne."
            )

        if self._is_explanation_request(user_text) and variant_matches:
            return self._build_explanation_reply(variant_matches)

        if self._is_recommendation_request(user_text) and variant_matches:
            return self._build_recommendation_reply(variant_matches)

        if (self._is_pricing_intent(user_text) or self._is_option_request(user_text)) and variant_matches:
            return self._build_variant_offer_reply(lead, variant_matches)

        if self._should_request_media(lead, topic, variant_matches, strict_match):
            return (
                f"Dla modelu {lead.device_model_raw} moge juz wstepnie podpowiedziec kierunek, ale tutaj zdjecie lub krotkie video naprawde pomoze rozroznic wariant naprawy. "
                "Jesli dolaczysz media, zawęże opcje i podam bardziej trafna wycene."
            )

        if strict_match:
            return (
                f"Dla {lead.device_model_raw} mamy gotowa pozycje: {strict_match.title} za okolo {strict_match.base_price:.2f} PLN. "
                f"{self._clean_sentence(strict_match.description) or 'Jesli chcesz, porownam ten wariant z innymi opcjami i podpowiem, co bedzie najrozsadniejsze.'}"
            )

        if catalog_matches:
            return self._build_soft_catalog_reply(lead, catalog_matches)

        if self.runtime.get_google_api_key():
            ai_reply = self._ask_gemini_fallback(lead, user_text, history_text, topic)
            if ai_reply:
                return ai_reply

        return self._generic_consultant_reply(lead, topic)

    def _update_lead_snapshot_from_text(self, lead, user_text: str) -> None:
        """Aktualizuje model, telefon i dane klienta na podstawie tekstu bez gubienia kontekstu."""

        model_guess = self.matcher.find_best_match(user_text, score_cutoff=86)
        if model_guess:
            lead.device_model_raw = f"{model_guess.brand} {model_guess.model_name}"
            lead.matched_device_id = model_guess.id
        elif not lead.device_model_raw:
            extracted_model = self._extract_device_reference(user_text)
            if extracted_model:
                lead.device_model_raw = extracted_model

        phone_match = re.search(r"(\+?\d[\d\-\s]{7,}\d)", user_text)
        if phone_match:
            lead.phone = phone_match.group(1).strip()

        explicit_name = re.search(r"(?:mam na imie|nazywam sie|to ja)\s+([A-Za-zÀ-ÿ' -]{2,80})", user_text, re.IGNORECASE)
        if explicit_name:
            lead.customer_name = explicit_name.group(1).strip(" .,-")
        elif phone_match and not lead.customer_name:
            possible_name = re.sub(r"\+?\d[\d\-\s]{7,}\d", "", user_text).strip(" ,.-")
            if possible_name and len(possible_name.split()) >= 2 and any(char.isalpha() for char in possible_name):
                lead.customer_name = possible_name[:120]

    def _build_variant_offer_reply(self, lead, variants) -> str:
        """Buduje konsultacyjna odpowiedz z wariantami i roznicami."""

        variants = variants[:3]
        options = [f"{item.title} za okolo {item.base_price:.2f} PLN" for item in variants]
        joined = ", ".join(options[:-1]) + f" oraz {options[-1]}" if len(options) > 1 else options[0]
        difference = self._summarize_variant_difference(variants)
        return (
            f"Dla {lead.device_model_raw} widze kilka realnych opcji: {joined}. "
            f"{difference} "
            "Jesli chcesz, od razu podpowiem, ktory wariant bedzie najlepszy przy nizszym budzecie, a ktory jest najbezpieczniejszy na dluzszy czas."
        )

    def _build_explanation_reply(self, variants) -> str:
        """Wyjasnia, co oznacza wybrany wariant i czym rozni sie od innych."""

        chosen = variants[0]
        difference = self._summarize_variant_difference(variants)
        description = self._clean_sentence(chosen.description)
        return (
            f"W praktyce chodzi o wariant {chosen.title} za okolo {chosen.base_price:.2f} PLN. "
            f"{description or difference} "
            "Jesli chcesz, porownam to od razu z pozostalymi opcjami i powiem, co bardziej sie oplaca."
        )

    def _build_recommendation_reply(self, variants) -> str:
        """Rekomenduje najlepszy wariant zalezenie od jakosci lub budzetu."""

        best_quality = self._pick_best_quality_variant(variants)
        best_budget = min(variants, key=lambda item: item.base_price)
        if best_quality.id == best_budget.id:
            return (
                f"Najrozsadniej wyglada teraz {best_quality.title} za okolo {best_quality.base_price:.2f} PLN, bo dobrze laczy koszt i efekt naprawy. "
                "Jesli chcesz, moge od razu zapisac kontakt do serwisu albo odpowiedziec, jak ta opcja wypada pod wzgledem trwalosci."
            )
        return (
            f"Jesli chcesz zejsc z kosztem, najtanszy bedzie {best_budget.title} za okolo {best_budget.base_price:.2f} PLN. "
            f"Jesli zalezy Ci bardziej na spokoju i jakosci, lepszym wyborem bedzie {best_quality.title} za okolo {best_quality.base_price:.2f} PLN. "
            "Moge od razu powiedziec, dla kogo lepsza jest kazda z tych opcji."
        )

    def _build_soft_catalog_reply(self, lead, catalog_matches) -> str:
        """Daje naturalna odpowiedz, gdy jest sensowny kierunek, ale nie ma twardego kompletu wariantow."""

        top = catalog_matches[0]
        description = self._clean_sentence(top.description)
        return (
            f"Wyglada na to, ze dla {lead.device_model_raw} najblizsza usluga to {top.title} za okolo {top.base_price:.2f} PLN. "
            f"{description or 'Jesli chcesz, moge sprawdzic, czy mamy tez tansza albo mocniejsza opcje i od razu wyjasnic roznice.'}"
        )

    def _generic_consultant_reply(self, lead, topic: str) -> str:
        """Odpowiedz awaryjna, ale nadal konsultacyjna i leadowa."""

        if not lead.device_model_raw:
            return (
                "Jasne, pomoge. Podaj prosze model urzadzenia i opisz objaw, a od razu powiem, jakie sa realne warianty naprawy i co najbardziej sie oplaca."
            )
        if topic == "battery":
            return (
                f"Dla {lead.device_model_raw} moge porownac kilka wariantow wymiany baterii i wyjasnic, czym beda sie roznily pod wzgledem ceny, jakosci i komunikatow systemowych. "
                "Jesli chcesz, od razu przejde do konkretnych opcji."
            )
        return (
            f"Dla {lead.device_model_raw} moge przeanalizowac najlepsze warianty naprawy i podpowiedziec, ktore rozwiazanie bedzie najbardziej rozsadne cenowo. "
            "Jesli chcesz, przejde od razu do konkretow."
        )

    def _ask_gemini_fallback(self, lead, user_text: str, history_text: str, topic: str) -> str | None:
        """Uzywa Gemini tylko jako awaryjnego konsultanta, gdy katalog nie daje dobrej odpowiedzi."""

        try:
            from google import genai
            from google.genai import types
        except Exception:
            return None

        try:
            client = genai.Client(api_key=self.runtime.get_google_api_key())
            config = self.runtime.load()
            prompt = (
                "Jestes bardzo dobrym konsultantem serwisu elektroniki. "
                "Rozmawiaj po polsku, naturalnie i konkretnie. "
                "Twoim zadaniem jest wyjasnic problem klienta, zaproponowac najlepsze rozwiazania i delikatnie prowadzic do zostawienia kontaktu. "
                "Nie pisz jak bot. Nie uzywaj markdown ani list. "
                "Odpowiedz w 3 do 5 zdaniach. "
                "Jesli sa co najmniej 2 realne warianty, nazwij je i wyjasnij roznice. "
                "Pros o zdjecie albo video tylko wtedy, gdy bez tego nie da sie sensownie zawezic diagnozy. "
                "Dla Apple trzymaj sie cen z iflix lub bardzo blisko nich. "
                f"Nazwa serwisu: {config.get('business_name') or 'Serwis'}\n"
                f"Telefon serwisu: {config.get('business_phone') or 'brak'}\n"
                f"Godziny pracy: {config.get('working_hours') or 'brak'}\n"
                f"Model klienta: {lead.device_model_raw or 'nieznany'}\n"
                f"Temat: {topic}\n"
                f"Historia: {history_text}\n"
                f"Ostatnia wiadomosc klienta: {user_text}"
            )
            response = client.models.generate_content(
                model=self.runtime.get_gemini_model(),
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.45),
            )
            cleaned = self._clean_response(response.text or "")
            return cleaned or None
        except Exception:
            return None

    def _find_variant_matches(self, catalog_matches):
        """Szuka wariantow tej samej uslugi na podstawie nazw i opisow."""

        if len(catalog_matches) < 2:
            return catalog_matches

        def family_key(item) -> str:
            text = f"{getattr(item, 'title', '')} {getattr(item, 'description', '')}".lower()
            for token in [
                "oryginal", "oryginał", "zamiennik", "premium", "copy",
                "bez przypisania", "z przypisaniem", "przypisanie",
                "bez programowania", "z programowaniem", "programowanie",
            ]:
                text = text.replace(token, " ")
            return " ".join(text.split())

        first_key = family_key(catalog_matches[0])
        same_family = [item for item in catalog_matches if family_key(item) == first_key]
        return same_family if len(same_family) >= 2 else catalog_matches

    def _summarize_variant_difference(self, variants) -> str:
        """Streszcza sens roznic miedzy wariantami tak, jak tlumaczylby to handlowiec."""

        titles = " ".join((item.title or "").lower() for item in variants)
        descriptions = " ".join((item.description or "").lower() for item in variants)
        combined = f"{titles} {descriptions}"

        if "oryg" in combined and ("zamien" in combined or "copy" in combined):
            return "Tanszy wariant zwykle pozwala zejsc z kosztem, a oryginal daje lepsza jakosc i wiekszy spokoj na dluzszy czas."
        if "przypis" in combined:
            return "Roznica polega glownie na tym, czy bateria jest przypisana do systemu, co moze miec znaczenie dla komunikatow i wygody uzytkowania."
        if "program" in combined:
            return "Roznica wynika glownie z zakresu uslugi, na przyklad z dodatkowej konfiguracji lub programowania."
        if "premium" in combined:
            return "Roznica dotyczy glownie jakosci czesci i przewidywanej trwalosci po naprawie."
        return "Roznica dotyczy najczesciej jakosci czesci, trwalosci albo zakresu wykonanej uslugi."

    def _pick_best_quality_variant(self, variants):
        """Wybiera wariant, ktory brzmi najlepiej jakosciowo."""

        def score(item):
            text = f"{item.title} {item.description or ''}".lower()
            value = 0
            if "oryg" in text:
                value += 4
            if "premium" in text:
                value += 3
            if "zamien" in text:
                value += 1
            if "przypis" in text:
                value += 1
            return (value, item.base_price)

        return sorted(variants, key=score, reverse=True)[0]

    def _should_request_media(self, lead, topic: str, variant_matches, strict_match) -> bool:
        """Media prosimy tylko wtedy, gdy bez nich nie da sie sensownie odroznic uszkodzenia wizualnego."""

        if lead.media_assets or strict_match or len(variant_matches) >= 2:
            return False
        return topic in {"screen", "glass", "body", "water"}

    @staticmethod
    def _detect_topic(text: str) -> str:
        value = (text or "").lower()
        if any(token in value for token in ["bateria", "akumulator", "slabo trzyma", "słabo trzyma", "nie laduje", "nie ładuje"]):
            return "battery"
        if any(token in value for token in ["ekran", "wyswietlacz", "wyświetlacz", "dotyk", "lcd", "oled"]):
            return "screen"
        if any(token in value for token in ["szklo", "szybka", "plecki", "plecy", "obudowa", "klapka"]):
            return "body"
        if any(token in value for token in ["zalany", "woda", "po zalaniu"]):
            return "water"
        if any(token in value for token in ["wirus", "virus", "windows", "reinstalacja", "system"]):
            return "software"
        return "unknown"

    @staticmethod
    def _is_pricing_intent(text: str) -> bool:
        value = (text or "").lower()
        return any(token in value for token in ["ile kosztuje", "jaka cena", "koszt", "wycena", "cena"])

    @staticmethod
    def _is_option_request(text: str) -> bool:
        value = (text or "").lower()
        return any(token in value for token in [
            "inna opcja", "inne opcje", "sa jeszcze", "są jeszcze", "czy jest cos tanszego",
            "czy jest coś tańszego", "da sie na", "da się na", "zamiennik", "oryginal", "oryginał",
            "propozycje", "wariant", "warianty",
        ])

    @staticmethod
    def _is_recommendation_request(text: str) -> bool:
        value = (text or "").lower()
        return any(token in value for token in [
            "co polecasz", "co lepsze", "ktore lepsze", "które lepsze", "co bardziej sie oplaca",
            "co bardziej się opłaca", "co wybrac", "co wybrać", "najlepsze rozwiazanie", "najlepsze rozwiązanie",
        ])

    @staticmethod
    def _is_explanation_request(text: str) -> bool:
        value = (text or "").lower()
        return any(token in value for token in [
            "co znaczy", "co to znaczy", "jaka roznica", "jaka różnica",
            "czym sie rozni", "czym się różni", "o co chodzi", "wyjasnij", "wyjaśnij",
        ])

    @staticmethod
    def _history_context(lead) -> str:
        if not getattr(lead, "messages", None):
            return ""
        recent = [item.message_text for item in lead.messages[-6:] if getattr(item, "message_text", None)]
        return " ".join(recent)

    @staticmethod
    def _clean_sentence(text: str | None) -> str:
        value = re.sub(r"\s+", " ", (text or "").strip())
        return value

    @staticmethod
    def _clean_response(text: str) -> str:
        cleaned = re.sub(r"[*_#`>-]+", " ", text or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        return " ".join(sentence.strip() for sentence in sentences[:5] if sentence.strip())

    @staticmethod
    def _extract_device_reference(text: str) -> str | None:
        patterns = [
            r"(iphone\s?(?:se|x|xr|xs|11|12|13|14|15|16)(?:\s?(?:pro|max|mini|plus))?)",
            r"(ipad\s?[a-z0-9+\- ]{1,20})",
            r"(samsung\s+galaxy\s?[a-z0-9+\- ]{1,20})",
            r"(galaxy\s?[a-z0-9+\- ]{1,20})",
            r"(macbook\s?[a-z0-9+\- ]{0,20})",
        ]
        source = (text or "").lower()
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split()).strip(" .,-")
        return None

    @staticmethod
    def _try_build_closing_reply(lead, user_text: str) -> str | None:
        if not (lead.customer_name and lead.phone):
            return None
        text = (user_text or "").lower().strip()
        if any(token in text for token in ["dziekuje", "dziękuję", "ok", "okej", "super", "do zobaczenia"]) and len(text.split()) <= 6:
            return (
                "Super, mam juz komplet danych i przekazuje zgloszenie do serwisu. "
                "Skontaktujemy sie, aby potwierdzic dogodny termin. Do uslyszenia."
            )
        return None
