import re

from app.services.device_matcher import DeviceMatcherService
from app.services.repair_catalog_service import RepairCatalogService
from app.services.runtime_config_service import RuntimeConfigService


class ConsultantService:
    """Prowadzi rozmowe z klientem jak konsultant serwisu i korzysta z katalogu napraw."""

    def __init__(self, db) -> None:
        self.db = db
        self.catalog = RepairCatalogService(db)
        self.matcher = DeviceMatcherService(db)
        self.runtime = RuntimeConfigService()

    def build_reply(self, lead, user_text: str) -> str:
        """Buduje odpowiedz konsultanta, najpierw z katalogu napraw, potem z AI lub heurystyki."""

        model_guess = self.matcher.find_best_match(user_text, score_cutoff=82)
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

        name_match = re.search(r"(?:mam na imie|nazywam sie|to ja)\s+([A-Za-zÀ-ÿ' -]{2,80})", user_text, re.IGNORECASE)
        if name_match:
            lead.customer_name = name_match.group(1).strip(" .,-")
        elif phone_match and not lead.customer_name:
            inline_name = re.sub(r"\+?\d[\d\-\s]{7,}\d", "", user_text).strip(" ,.-")
            if inline_name and len(inline_name.split()) >= 2 and any(char.isalpha() for char in inline_name):
                lead.customer_name = inline_name[:120]

        closing_reply = self._try_build_closing_reply(lead, user_text)
        if closing_reply:
            return closing_reply

        catalog_query = " ".join(filter(None, [lead.device_model_raw, user_text]))
        strict_match = self.catalog.find_strict_match(catalog_query)
        catalog_matches = self.catalog.find_best_matches(catalog_query)
        if strict_match and (not catalog_matches or catalog_matches[0].id != strict_match.id):
            catalog_matches = [strict_match, *catalog_matches][:3]
        pricing_intent = self._is_pricing_intent(user_text)
        variant_matches = self._find_variant_matches(catalog_matches)

        if pricing_intent and len(variant_matches) >= 2:
            return self._build_catalog_options_reply(variant_matches[:3])

        if pricing_intent and strict_match:
            return (
                f"Dla tej naprawy mamy gotową pozycję w cenniku: {strict_match.title} za około {strict_match.base_price:.2f} PLN. "
                "Jeśli chcesz, mogę od razu zapisać kontakt do serwisu albo podpowiedzieć, czy istnieje tańsza lub wyższa jakościowo opcja."
            )

        if self.runtime.get_google_api_key():
            try:
                return self._ask_gemini(lead, user_text, catalog_matches, strict_match, variant_matches)
            except Exception:
                pass
        return self._fallback_reply(lead, user_text, catalog_matches, strict_match, variant_matches)

    def _ask_gemini(self, lead, user_text: str, catalog_matches, strict_match, variant_matches) -> str:
        """Uzywa Gemini jako konsultanta, podajac katalog i historie rozmowy."""

        from google import genai
        from google.genai import types

        config = self.runtime.load()
        client = genai.Client(api_key=self.runtime.get_google_api_key())
        recent_messages = lead.messages[-8:] if lead.messages else []
        history = "\n".join(
            f"{item.role.value}: {item.message_text}" for item in recent_messages
        )
        pricing_intent = self._is_pricing_intent(user_text)
        should_request_media = self._should_request_media(lead, user_text, catalog_matches, strict_match)
        catalog_context = "\n".join(
            f"- {item.title}: {item.base_price} PLN. {item.description or ''}".strip()
            for item in catalog_matches
        ) or "Brak bezposredniego dopasowania w katalogu napraw."
        variant_context = "\n".join(
            f"- {item.title}: {item.base_price} PLN. {item.description or ''}".strip()
            for item in variant_matches
        ) or "Brak kilku wyraznych wariantow tej samej naprawy."
        media_note = (
            "Klient dolaczyl media do zgloszenia."
            if lead.media_assets
            else "Klient jeszcze nie dolaczyl mediow."
        )
        prompt = (
            "Jestes ekspertem serwisu Apple/Samsung oraz laptopow z Windows. "
            "Rozmawiaj po polsku, badz uprzejmy i profesjonalny. "
            "Twoim celem jest nie tylko doradzic, ale tez delikatnie zamienic rozmowe w realne zgloszenie serwisowe. "
            "Prowadz rozmowe jak realny konsultant, dawaj sensowne warianty naprawy, ale odpowiadaj krotko i konkretnie. "
            "Najpierw sprawdz katalog napraw i jesli pasuje, wykorzystaj te ceny jako priorytet. "
            "Jesli jest scisle dopasowana usluga w katalogu, nie podawaj wyzszej ceny niz katalogowa bez bardzo wyraznego uzasadnienia. "
            "Jesli klient pyta o cene, dla Apple najpierw bierz ceny z iflix jako glowny punkt odniesienia, a dopiero potem z innych polskich serwisow. "
            "Nie zawyzaj cen wzgledem iflix. Jesli iflix ma nizsza i sensowna cene, trzymaj sie jej lub bardzo bliskiego zakresu. "
            "Jesli klient zostawil juz imie i telefon oraz potwierdza kontakt, zakoncz rozmowe krotko i uprzejmie bez dalszych pytan. "
            "Jesli nie ma dopasowania, mozesz podac orientacyjne warianty i zaznacz, ze to wstepna konsultacja. "
            "Jesli problem sugeruje kilka scenariuszy, podaj maksymalnie 2 lub 3 najlepsze opcje i w jednym zdaniu wyjasnij roznice miedzy nimi. "
            "Jesli w katalogu sa 2 lub 3 sensowne warianty tej samej naprawy, pokaz je od razu wszystkie i wyjasnij roznice w jakosci, trwalosci albo zakresie uslugi. "
            "Jesli klient jest zainteresowany, zaproponuj zapis do serwisu i zbierz imie i nazwisko oraz numer telefonu, jesli ich jeszcze nie ma. "
            "Nie odsylaj tylko do telefonu. Prowadz klienta do zostawienia kontaktu w czacie. "
            "Jesli brakuje modelu, dopytaj o model. "
            f"{'Mozesz poprosic o zdjecie lub krotkie video, ale tylko jesli bez mediow nie da sie realnie odroznic wariantu naprawy.' if should_request_media else 'Nie pros o zdjecie ani video, jesli juz da sie sensownie odpowiedziec bez mediow.'} "
            "Jesli w katalogu sa dwa sensowne warianty tej samej naprawy, pokaz oba od razu zamiast prosic o media. "
            "Odpowiedz ma miec 3 do 5 krotkich zdan. "
            "Nie uzywaj markdown, gwiazdek, list punktowanych, naglowkow ani emoji. "
            "Pisz ladnie, naturalnie i po ludzku.\n\n"
            f"Scisle dopasowanie katalogowe: {strict_match.title if strict_match else 'brak'} | "
            f"cena: {f'{strict_match.base_price:.2f} PLN' if strict_match else 'brak'}\n\n"
            f"Warianty tej samej naprawy:\n{variant_context}\n\n"
            f"Dane serwisu:\n"
            f"Nazwa: {config.get('business_name') or 'Serwis'}\n"
            f"Telefon: {config.get('business_phone') or 'brak'}\n"
            f"E-mail: {config.get('business_email') or 'brak'}\n"
            f"Adres: {config.get('business_address') or 'brak'}\n"
            f"Godziny pracy: {config.get('working_hours') or 'brak'}\n\n"
            f"Dane klienta:\n"
            f"Imie i nazwisko: {lead.customer_name or 'brak'}\n"
            f"Telefon: {lead.phone or 'brak'}\n"
            f"Model: {lead.device_model_raw or 'nieznany'}\n"
            f"{media_note}\n\n"
            f"Katalog napraw:\n{catalog_context}\n\n"
            f"Historia rozmowy:\n{history}\n\n"
            f"Ostatnia wiadomosc klienta: {user_text}"
        )
        response = client.models.generate_content(
            model=self.runtime.get_gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                tools=[types.Tool(google_search=types.GoogleSearch())] if pricing_intent else None,
            ),
        )
        cleaned = self._clean_response(response.text or "")
        return cleaned or self._fallback_reply(lead, user_text, catalog_matches, strict_match, variant_matches)

    def _fallback_reply(self, lead, user_text: str, catalog_matches, strict_match, variant_matches) -> str:
        """Heurystyczna odpowiedz, gdy AI jest niedostepne lub katalog juz wystarcza."""

        if len(variant_matches) >= 2 and self._is_pricing_intent(user_text):
            return self._build_catalog_options_reply(variant_matches[:3])

        if strict_match:
            return (
                f"Dla tej naprawy mamy juz gotowa pozycje w cenniku: {strict_match.title}. "
                f"Orientacyjna cena to {strict_match.base_price:.2f} PLN. "
                f"{strict_match.description or 'Jesli chcesz, od razu zapisze Twoje zgloszenie i kontakt do serwisu.'}"
            )

        if catalog_matches:
            top = catalog_matches[0]
            return (
                f"Wyglada na to, ze mamy podobna usluge w katalogu: {top.title}. "
                f"Orientacyjna cena startuje od {top.base_price:.2f} PLN. "
                f"{top.description or 'Jesli chcesz, moge od razu zapisac kontakt do oddzwonienia albo wizyty.'}"
            )

        text = user_text.lower()
        if "wirus" in text or "virus" in text or "windows" in text:
            return (
                "Widze tu dwa sensowne warianty. Jesli system jeszcze dziala stabilnie, zwykle wystarcza porzadne czyszczenie i usuniecie zagrozen. "
                "Jesli problem wraca albo Windows mocno zwalnia, bezpieczniejsza bywa pelna reinstalacja systemu. "
                "Moge od razu podpowiedziec, co obejmuje kazda opcja i w razie potrzeby zapisac Twoj numer do kontaktu."
            )
        if not lead.device_model_raw:
            return (
                "Jasne, pomoge. Napisz prosze model urzadzenia i co dokladnie sie dzieje. "
                "Jesli bez zdjecia lub video nie da sie odroznic wariantu naprawy, wtedy o nie poprosze."
            )
        if self._should_request_media(lead, user_text, catalog_matches, strict_match):
            return (
                f"Rozumiem. Dla modelu {lead.device_model_raw} moge przygotowac konkretniejsze warianty naprawy, ale tutaj zdjecie lub video faktycznie pomoze odroznic uszkodzenie. "
                "Dolacz prosze media i napisz, co dokladnie przestalo dzialac, a wtedy zawęzę wycenę i warianty."
            )
        return (
            f"Rozumiem. Dla modelu {lead.device_model_raw} moge juz podpowiedziec realne warianty naprawy bez proszenia o video. "
            "Jesli chcesz, podam konkretne opcje cenowe albo od razu pomoge zostawic kontakt do serwisu."
        )

    def _build_catalog_options_reply(self, catalog_matches) -> str:
        """Pokazuje dwa katalogowe warianty naprawy od razu, bez zbędnego dopytywania."""

        variants = catalog_matches[:3]
        if len(variants) == 1:
            item = variants[0]
            return f"Mamy taki wariant w cenniku: {item.title} za około {item.base_price:.2f} PLN. Jeśli chcesz, mogę od razu zapisać kontakt do serwisu."

        pieces = [f"{item.title} - około {item.base_price:.2f} PLN" for item in variants]
        difference = self._summarize_variant_difference(variants)
        joined = ", ".join(pieces[:-1]) + f" oraz {pieces[-1]}" if len(pieces) > 1 else pieces[0]
        return (
            f"Dla tej naprawy widzę kilka sensownych opcji: {joined}. "
            f"{difference} Jeśli chcesz, pomogę dobrać najlepszy wariant pod budżet albo od razu zapiszę kontakt do serwisu."
        )

    def _summarize_variant_difference(self, variants) -> str:
        """Buduje krótkie wyjaśnienie różnic między wariantami katalogowymi."""

        joined_descriptions = " ".join((item.description or "").lower() for item in variants)
        joined_titles = " ".join((item.title or "").lower() for item in variants)
        text = f"{joined_titles} {joined_descriptions}"

        if "oryg" in text and ("zamien" in text or "copy" in text):
            return "Zwykle tańsza opcja jest bardziej budżetowa, a oryginał daje lepszą jakość i większy spokój na dłużej."
        if "premium" in text and ("zamien" in text or "oryg" in text):
            return "Różnica zwykle wynika z jakości części albo poziomu wykonania usługi."
        if "program" in text:
            return "Różnica wynika głównie z zakresu usługi, na przykład z programowania lub dodatkowej konfiguracji."
        return "Różnica najczęściej dotyczy jakości części, trwałości albo zakresu wykonanej usługi."

    def _find_variant_matches(self, catalog_matches):
        """Wybiera warianty tej samej naprawy, aby móc pokazać klientowi więcej niż jedną opcję."""

        if len(catalog_matches) < 2:
            return catalog_matches

        def family_key(item) -> str:
            text = f"{getattr(item, 'title', '')} {getattr(item, 'description', '')}".lower()
            stop_words = [
                "oryginal",
                "oryginał",
                "zamiennik",
                "premium",
                "copy",
                "bez programowania",
                "z programowaniem",
                "programowanie",
            ]
            for token in stop_words:
                text = text.replace(token, " ")
            return " ".join(text.split())

        first_key = family_key(catalog_matches[0])
        variants = [item for item in catalog_matches if family_key(item) == first_key]
        return variants if len(variants) >= 2 else catalog_matches

    def _should_request_media(self, lead, user_text: str, catalog_matches, strict_match) -> bool:
        """Prosi o media tylko wtedy, gdy bez nich nie da się sensownie odróżnić wariantu naprawy."""

        if lead.media_assets:
            return False
        if strict_match or len(catalog_matches) >= 2:
            return False

        text = (user_text or "").lower()
        explicit_symptoms = [
            "bateria",
            "akumulator",
            "nie laduje",
            "nie ładuje",
            "wirus",
            "virus",
            "windows",
            "reinstalacja",
            "instalacja",
            "zawias",
            "klawiatura",
            "glosnik",
            "głośnik",
            "mikrofon",
        ]
        if any(token in text for token in explicit_symptoms):
            return False

        visual_damage = [
            "ekran",
            "wyswietlacz",
            "wyświetlacz",
            "szklo",
            "szybka",
            "plecki",
            "plecy",
            "obudowa",
            "zbity",
            "pęk",
            "pek",
        ]
        return any(token in text for token in visual_damage)

    @staticmethod
    def _clean_response(text: str) -> str:
        """Czysci odpowiedz modelu z markdown i skraca ja do kilku zdan."""

        cleaned = re.sub(r"[*_#`>-]+", " ", text or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        return " ".join(sentence.strip() for sentence in sentences[:4] if sentence.strip())

    @staticmethod
    def _extract_device_reference(text: str) -> str | None:
        """Probuje wyciagnac model urzadzenia nawet wtedy, gdy nie ma go w lokalnej bazie."""

        patterns = [
            r"(iphone\s?[a-z0-9+\- ]{1,20})",
            r"(samsung\s+galaxy\s?[a-z0-9+\- ]{1,20})",
            r"(galaxy\s?[a-z0-9+\- ]{1,20})",
        ]
        source = (text or "").lower()
        for pattern in patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split()).strip(" .,-")
        return None

    @staticmethod
    def _is_pricing_intent(text: str) -> bool:
        """Sprawdza, czy klient pyta glownie o koszt lub rodzaje naprawy."""

        value = (text or "").lower()
        keywords = ["ile kosztuje", "jaka cena", "koszt", "wycena", "cena", "rodzaje naprawy"]
        return any(keyword in value for keyword in keywords)

    @staticmethod
    def _try_build_closing_reply(lead, user_text: str) -> str | None:
        """Zamyka rozmowe krotko, gdy lead jest juz kompletny i klient potwierdza kontakt."""

        if not (lead.customer_name and lead.phone):
            return None
        text = (user_text or "").lower().strip()
        closing_signals = ["dziękuję", "dziekuje", "do zobaczenia", "ok", "okej", "tak", "pasuje", "będzie", "bedzie", "super"]
        if any(signal in text for signal in closing_signals) and len(text.split()) <= 6:
            return (
                "Super, mam już komplet danych i przekazuję zgłoszenie do serwisu. "
                "Skontaktujemy się, aby potwierdzić dogodny termin. Do usłyszenia."
            )
        return None
