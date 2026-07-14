from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OutModel


class CurrentUser(BaseModel):
    """The authenticated user resolved by ``get_current_user``.

    Carries only identity fields — never session tokens or internal Mongo
    IDs. Returned to endpoints as a typed value so routes can't
    accidentally leak ``_session_token`` or ``_id`` into responses.
    """

    model_config = ConfigDict(extra="ignore")

    user_id: str
    email: str
    auth_provider: Optional[str] = None
    supabase_user_id: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None


class UserOut(OutModel):
    user_id: str
    email: str
    auth_provider: Optional[str] = None
    supabase_user_id: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None


class AuthSessionOut(OutModel):
    session_token: Optional[str] = None
    user: UserOut


class MeOut(OutModel):
    user: UserOut


class GoogleSessionIn(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    state: str = Field(default="", max_length=256)


class SupabaseSessionIn(BaseModel):
    access_token: str = Field(min_length=1, max_length=8192)