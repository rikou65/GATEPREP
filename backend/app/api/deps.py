from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request

from app.integrations.supabase_auth import SupabaseAuthIntegration
from app.repositories.users import UserRepository
from app.schemas.auth import CurrentUser
from app.services.auth.supabase_service import SupabaseAuthService


async def get_current_user(request: Request) -> CurrentUser:
    """Resolve the authenticated user from cookie or Supabase Bearer token.

    Returns a typed ``CurrentUser`` so routes get attribute access and the
    response contract can't accidentally leak ``_session_token`` or ``_id``.

    Cookie path is lookup-only. Bearer path is also lookup-only —
    auto-link/user-create happens exclusively in ``POST /auth/supabase-session``.
    """
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="DB not available")

    session_token = request.cookies.get("session_token")
    if session_token:
        user_repo = UserRepository(db)
        user = await user_repo.find_by_session_token(session_token)
        if user is not None:
            return CurrentUser(**user)

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        supabase_token = auth.split(" ", 1)[1]
        settings = getattr(request.app.state, "settings", None)
        if settings is not None:
            supabase_integration = SupabaseAuthIntegration(
                supabase_url=getattr(settings, "SUPABASE_URL", ""),
                jwt_secret=getattr(settings, "SUPABASE_JWT_SECRET", ""),
                jwks_url=getattr(settings, "SUPABASE_JWKS_URL", ""),
            )
            user_repo = UserRepository(db)
            supabase_service = SupabaseAuthService(
                user_repo, supabase_integration
            )
            user = await supabase_service.resolve(supabase_token)
            if user is not None:
                return CurrentUser(**user)

    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_session_token(request: Request) -> Optional[str]:
    """Extract the raw session cookie value.

    Used only where the raw token is genuinely needed — logout (to delete
    the session row) and identity-repair (to repoint the session row).
    Never expose this token in a response body.
    """
    return request.cookies.get("session_token")