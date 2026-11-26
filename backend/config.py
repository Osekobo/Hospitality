from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Social-First AI Concierge"
    environment: str = "development"
    database_url: str = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/hospitality_db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
    demo_mode: bool = True
    admin_api_token: str = ""

    at_username: str = "sandbox"
    at_api_key: str = ""
    at_sandbox: bool = True
    at_sender_id: str = ""
    at_ussd_service_code: str = "*389#"
    at_webhook_secret: str = ""

    meta_app_secret: str = ""
    meta_verify_token: str = "change-this-verify-token"
    meta_api_version: str = "v21.0"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    instagram_access_token: str = ""
    instagram_page_id: str = "me"

    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = "174379"
    mpesa_passkey: str = ""
    mpesa_transaction_type: str = "CustomerPayBillOnline"
    mpesa_callback_url: str = "https://your-public-domain.com/mpesa/callback"
    mpesa_sandbox: bool = True
    reward_airtime_amount: float = 0.0

    ai_provider: str = "none"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    google_places_api_key: str = ""
    openweather_api_key: str = ""
    default_city: str = "Nairobi"

    @model_validator(mode="after")
    def validate_callback_url(self) -> "Settings":
        if self.mpesa_consumer_key and not self.mpesa_callback_url.rstrip("/").endswith("/mpesa/callback"):
            raise ValueError("MPESA_CALLBACK_URL must end with /mpesa/callback")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ai_enabled(self) -> bool:
        if self.ai_provider == "openai":
            return bool(self.openai_api_key)
        if self.ai_provider == "gemini":
            return bool(self.gemini_api_key)
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
