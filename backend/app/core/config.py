from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    MONGO_URL: str
    DB_NAME: str
    JWT_SECRET: str

    YOUTUBE_API_KEY: Optional[str] = ""

    GOOGLE_DRIVE_CLIENT_ID: Optional[str] = ""
    GOOGLE_DRIVE_CLIENT_SECRET: Optional[str] = ""
    GOOGLE_LOGIN_REDIRECT_URI: Optional[str] = ""
    GOOGLE_DRIVE_REDIRECT_URI: Optional[str] = ""
    GOOGLE_YOUTUBE_REDIRECT_URI: Optional[str] = ""

    FRONTEND_URL: Optional[str] = ""
    MISTRAL_API_KEY: Optional[str] = ""

    SUPABASE_URL: Optional[str] = ""
    SUPABASE_JWT_SECRET: Optional[str] = ""
    SUPABASE_JWKS_URL: Optional[str] = ""
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = ""

    TOKEN_ENCRYPTION_KEY: Optional[str] = ""

    ENVIRONMENT: Optional[str] = "development"

    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
