from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    vapi_api_key: Optional[str] = Field(default=None)
    vapi_base_url: str = "https://api.vapi.ai"

    log_level: str = "INFO"
    timeout: int = 30

    # Optional organization ID for multi-tenant scenarios
    org_id: Optional[str] = None

    def __init__(self, **kwargs):
        # Try to find .env file in current working directory first
        cwd_env = Path.cwd() / ".env"

        # Build the settings with proper env file priority
        if cwd_env.exists():
            # If .env exists in current directory, use it
            super().__init__(_env_file=str(cwd_env), **kwargs)
        else:
            # Otherwise fall back to environment variables only
            super().__init__(**kwargs)

        # Check if vapi_api_key was loaded from either source
        if not self.vapi_api_key:
            # Try to get from OS environment as fallback
            self.vapi_api_key = os.getenv("VAPI_API_KEY")

        # Validate that we have the API key
        if not self.vapi_api_key:
            raise ValueError(
                "VAPI_API_KEY not found. Please set it in:\n"
                "1. .env file in your project root directory, or\n"
                "2. As an environment variable VAPI_API_KEY"
            )


settings = Settings()