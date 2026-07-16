from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_user, get_session_token
from app.api.providers import (
    get_google_oauth_integration,
    get_session_repo,
    get_session_service,
    get_settings,
    get_oauth_state_service,
    get_identity_repair_service,
    get_supabase_auth_service,
)
from app.api.responses import err, ok
from app.schemas.auth import (
    AuthSessionOut,
    CurrentUser,
    GoogleSessionIn,
    MeOut,
    SupabaseSessionIn,
)
from app.schemas.common import Envelope, GoogleUrlOut, LoggedOut
from app.services.auth.identity_repair_service import IdentityRepairService
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.auth.session_service import SessionService
from app.services.auth.supabase_service import SupabaseAuthService

router = APIRouter()


@router.get("/auth/google-url", response_model=Envelope[GoogleUrlOut])
async def google_auth_url(
    google_oauth=Depends(get_google_oauth_integration),
    oauth_state_service: OAuthStateService = Depends(get_oauth_state_service),
):
    if not google_oauth.client_id:
        return err("config", "Google login not configured", 500)

    state = await oauth_state_service.generate("", "login")
    return ok({"authorization_url": google_oauth.build_login_url(state)})


@router.post("/auth/session", response_model=Envelope[AuthSessionOut])
async def auth_session(
    body: GoogleSessionIn,
    response: Response,
    settings=Depends(get_settings),
    google_oauth=Depends(get_google_oauth_integration),
    session_service: SessionService = Depends(get_session_service),
):
    code = body.code
    state = body.state
    if not state:
        return err("missing_state", "OAuth state required", 400)

    result = await session_service.login_with_google(code, state, google_oauth)
    if result is None:
        return err("auth_failed", "Invalid or expired OAuth state", 401)

    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=True,
        secure=settings.is_production(),
        samesite="lax",
        path="/",
        max_age=7 * 24 * 3600,
    )
    return ok({"user": result["user"]})


@router.post("/auth/dev-login", response_model=Envelope[AuthSessionOut])
async def dev_login(
    response: Response,
    settings=Depends(get_settings),
    session_service: SessionService = Depends(get_session_service),
):
    if settings.ENVIRONMENT != "development":
        return err("disabled", "Dev login is only available in development", 403)

    result = await session_service.login_dev()
    response.set_cookie(
        key="session_token",
        value=result["session_token"],
        httponly=True,
        max_age=604800,
        samesite="lax",
    )
    return ok({"user": result["user"]})


@router.post("/auth/supabase-session", response_model=Envelope[AuthSessionOut])
async def supabase_session(
    body: SupabaseSessionIn,
    response: Response,
    settings=Depends(get_settings),
    session_repo=Depends(get_session_repo),
    supabase_service: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    if not supabase_service.enabled:
        return err(
            "not_configured",
            "Supabase authentication is not configured",
            501,
        )

    user = await supabase_service.authenticate(body.access_token)
    if user is None:
        return err("auth_failed", "Invalid Supabase session", 401)

    session_token = await session_repo.create_session(user["user_id"])
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=settings.is_production(),
        samesite="lax",
        path="/",
        max_age=7 * 24 * 3600,
    )
    return ok({"user": user})


@router.get("/auth/me", response_model=Envelope[MeOut])
async def auth_me(user: CurrentUser = Depends(get_current_user)):
    return ok({"user": user})


@router.get("/auth/identity-audit", response_model=Envelope[dict])
async def identity_audit(
    user: CurrentUser = Depends(get_current_user),
    service: IdentityRepairService = Depends(get_identity_repair_service),
):
    return ok(await service.audit(user))


@router.post("/auth/repair-identity", response_model=Envelope[dict])
async def repair_identity(
    user: CurrentUser = Depends(get_current_user),
    session_token: str = Depends(get_session_token),
    service: IdentityRepairService = Depends(get_identity_repair_service),
):
    result = await service.repair(user, session_token)
    public_user = result.get("user") or {}
    result["user"] = public_user
    return ok(result)


@router.post("/auth/logout", response_model=Envelope[LoggedOut])
async def auth_logout(
    response: Response,
    token: str = Depends(get_session_token),
    session_repo=Depends(get_session_repo),
):
    if token:
        await session_repo.delete_session(token)
    response.delete_cookie("session_token", path="/")
    return ok({"logged_out": True})
