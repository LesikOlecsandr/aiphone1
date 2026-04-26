from pydantic import BaseModel, Field, model_validator


class ControlBootstrapResponse(BaseModel):
    """Stan startowy technicznego centrum zarzadzania."""

    is_setup: bool
    is_authenticated: bool


class ControlLoginRequest(BaseModel):
    """Dane logowania do technicznego panelu."""

    password: str = Field(min_length=6, max_length=256)


class ControlSetupRequest(BaseModel):
    """Pierwsza konfiguracja panelu i zabezpieczen."""

    password: str = Field(min_length=6, max_length=256)
    confirm_password: str = Field(min_length=6, max_length=256)
    business_name: str = Field(default="AI Repair Estimator", min_length=2, max_length=128)
    business_phone: str | None = Field(default=None, max_length=64)
    business_email: str | None = Field(default=None, max_length=128)
    business_address: str | None = Field(default=None, max_length=256)
    working_hours: str | None = Field(default=None, max_length=256)
    gemini_api_key: str | None = Field(default=None, max_length=512)
    gemini_model: str = Field(default="gemini-2.5-flash", min_length=3, max_length=128)

    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Wymaga zgodnosci hasla i potwierdzenia podczas pierwszej konfiguracji."""

        if self.password != self.confirm_password:
            raise ValueError("Hasla nie sa identyczne.")
        return self


class ControlConfigRead(BaseModel):
    """Odczyt technicznej i publicznej konfiguracji serwisu."""

    business_name: str
    business_phone: str | None = None
    business_email: str | None = None
    business_address: str | None = None
    working_hours: str | None = None
    widget_title: str
    widget_button_label: str
    accent_label: str
    gemini_model: str
    gemini_api_key_masked: str | None = None
    has_gemini_api_key: bool


class ControlConfigUpdate(BaseModel):
    """Aktualizacja konfiguracji panelu i widzetu."""

    business_name: str = Field(min_length=2, max_length=128)
    business_phone: str | None = Field(default=None, max_length=64)
    business_email: str | None = Field(default=None, max_length=128)
    business_address: str | None = Field(default=None, max_length=256)
    working_hours: str | None = Field(default=None, max_length=256)
    widget_title: str = Field(default="Wycen naprawe", min_length=2, max_length=128)
    widget_button_label: str = Field(default="Wycen naprawe", min_length=2, max_length=128)
    accent_label: str = Field(default="AI Konsultant", min_length=2, max_length=128)
    gemini_model: str = Field(default="gemini-2.5-flash", min_length=3, max_length=128)
    gemini_api_key: str | None = Field(default=None, max_length=512)
    new_admin_password: str | None = Field(default=None, min_length=6, max_length=256)
    new_admin_password_confirm: str | None = Field(default=None, min_length=6, max_length=256)

    @model_validator(mode="after")
    def validate_new_passwords_match(self):
        """Pilnuje zgodnosci nowego hasla w panelu technicznym."""

        if self.new_admin_password or self.new_admin_password_confirm:
            if not self.new_admin_password or not self.new_admin_password_confirm:
                raise ValueError("Podaj i potwierdz nowe haslo administratora.")
            if self.new_admin_password != self.new_admin_password_confirm:
                raise ValueError("Nowe hasla administratora nie sa identyczne.")
        return self


class ControlStatsRead(BaseModel):
    """Podstawowe statystyki dla panelu."""

    total_leads: int
    estimated_leads: int
    total_estimates: int
    average_estimate_value: float
    repair_catalog_size: int
