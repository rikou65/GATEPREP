from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, Request

from app.integrations.supabase_auth import SupabaseAuthIntegration
from app.repositories.users import UserRepository
from app.services.auth.supabase_service import SupabaseAuthService


async def get_current_user(request: Request) -> Dict[str, Any]:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="DB not available")

    session_token = request.cookies.get("session_token")
    if session_token:
        user_repo = UserRepository(db)
        user = await user_repo.find_by_session_token(session_token)
        if user is not None:
            user["_session_token"] = session_token
            return user

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
            user = await supabase_service.authenticate(supabase_token)
            if user is not None:
                return user

    raise HTTPException(status_code=401, detail="Not authenticated")
