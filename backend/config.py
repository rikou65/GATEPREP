from __future__ import annotations

from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URL: str
    DB_NAME: str
    JWT_SECRET: str

    YOUTUBE_API_KEY: Optional[str] = ""
    ADMIN_EMAILS: Optional[str] = ""

    GOOGLE_DRIVE_CLIENT_ID: Optional[str] = ""
    GOOGLE_DRIVE_CLIENT_SECRET: Optional[str] = ""
    GOOGLE_LOGIN_REDIRECT_URI: Optional[str] = ""
    GOOGLE_DRIVE_REDIRECT_URI: Optional[str] = ""

    FRONTEND_URL: Optional[str] = ""
    GEMINI_API_KEY: Optional[str] = ""
    LLAMA_CLOUD_API_KEY: Optional[str] = ""
    AUTH_PROVIDER_URL: str = "https://auth.example.com"
    AUTH_VERIFY_URL: str = "https://api.example.com/auth/verify"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def ADMIN_EMAILS_LIST(self) -> List[str]:
        return [e.strip() for e in (self.ADMIN_EMAILS or "").split(",") if e.strip()]
