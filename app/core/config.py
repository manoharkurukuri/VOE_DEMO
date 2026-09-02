from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Vehicle Offer Extraction API"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    local_storage_dir: str = "./storage/offers"
    app_timezone: str = "Asia/Kolkata"

    llm_provider: str = "gemini"

    gemini_api_key: SecretStr = SecretStr("")
    # Optional comma-separated keys; each concurrent LLM call uses a distinct key
    # to spread load past a single key's rate limit. Falls back to gemini_api_key.
    gemini_api_keys: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_timeout_seconds: int = 120
    gemini_max_retries: int = 2
    # Cap completion size so long multi-offer outputs don't get truncated
    # mid-JSON. Offer-rich dealer pages can exceed 8k tokens of structured output,
    # which fails the parse and loses every offer, so keep this generous.
    gemini_max_tokens: int = 32000

    max_body_chars: int = 350_000
    # Number of dealer URLs scraped/extracted in parallel. Each worker runs its
    # own headless browser + LLM call, so raise it only as far as CPU/RAM and the
    # LLM provider's rate limits allow.
    scraper_max_workers: int = 5
    # Number of dealers whose offers are extracted (stage C) in parallel. Each
    # dealer's URLs go to the LLM sequentially, so keep this near the API-key
    # count so concurrent dealers each get their own key.
    dealer_extract_workers: int = 5
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def resolved_api_keys(self) -> list[str]:
        """All Gemini API keys, preferring the multi-key list, else the single key."""
        raw = self.gemini_api_keys.get_secret_value().strip()
        if raw:
            keys = [key.strip() for key in raw.split(",") if key.strip()]
            if keys:
                return keys
        single = self.gemini_api_key.get_secret_value().strip()
        return [single] if single else []

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()