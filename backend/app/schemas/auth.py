from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    user_id: str
    auth_provider: Optional[str] = "legacy_google"
    supabase_user_id: Optional[str] = None
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    legacy_google_id: Optional[str] = None
    email_verified: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserSession(BaseModel):
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime


class OAuthState(BaseModel):
    state: str
    user_id: str
    purpose: str
    expires_at: datetime
    used: bool = False


class LoginResponse(BaseModel):
    session_token: str
    user: Dict[str, Any]


class CurrentUserOut(BaseModel):
    user: Dict[str, Any]
