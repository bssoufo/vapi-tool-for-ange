from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    vapi_api_key: str
    vapi_base_url: str = "https://api.vapi.ai"

    log_level: str = "INFO"
    timeout: int = 30

    # Optional organization ID for multi-tenant scenarios
    org_id: Optional[str] = None


settings = Settings()