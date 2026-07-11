from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.core.config import Settings
from app.integrations.google_oauth import GoogleOAuthIntegration
from app.integrations.supabase_auth import SupabaseAuthIntegration
from app.repositories.oauth_states import OAuthStateRepository
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.auth.identity_repair_service import IdentityRepairService
from app.services.auth.session_service import SessionService
from app.services.auth.supabase_service import SupabaseAuthService
from app.services.auth.user_service import UserService

router = APIRouter()


def _get_db(request: Request):
    return request.app.state.db


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


def _build_session_service(db, settings: Settings):
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)
    oauth_state_repo = OAuthStateRepository(db)
    oauth_state_service = OAuthStateService(oauth_state_repo)
    user_service = UserService(user_repo, session_repo)
    return SessionService(session_repo, oauth_state_service, user_service)


def _build_google_oauth(settings: Settings) -> GoogleOAuthIntegration:
    return GoogleOAuthIntegration(
        settings.GOOGLE_DRIVE_CLIENT_ID,
        settings.GOOGLE_DRIVE_CLIENT_SECRET,
        settings.GOOGLE_LOGIN_REDIRECT_URI,
    )


def _build_oauth_state_service(db) -> OAuthStateService:
    return OAuthStateService(OAuthStateRepository(db))


@router.get("/auth/google-url")
async def google_auth_url(request: Request):
    settings = _get_settings(request)
    google_oauth = _build_google_oauth(settings)
    if not google_oauth.client_id:
        return err("config", "Google login not configured", 500)
    oauth_state_service = _build_oauth_state_service(_get_db(request))
    state = await oauth_state_service.generate("", "login")
    return ok({"authorization_url": google_oauth.build_login_url(state)})


@router.post("/auth/session")
async def auth_session(request: Request, response: Response):
    settings = _get_settings(request)
    db = _get_db(request)
    session_service = _build_session_service(db, settings)
    google_oauth = _build_google_oauth(settings)

    body = await request.json()
    code = body.get("code")
    state = body.get("state", "")
    if not code:
        return err("missing_code", "Authorization code required", 400)
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


@router.post("/auth/dev-login")
async def dev_login(request: Request, response: Response):
    settings = _get_settings(request)
    db = _get_db(request)
    session_service = _build_session_service(db, settings)

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
    return ok({"session_token": result["session_token"], "user": result["user"]})


@router.post("/auth/supabase-session")
async def supabase_session(request: Request, response: Response):
    """Exchange a Supabase access token for a FastAPI session.

    Frontend sends the Supabase JWT, backend verifies it, maps to internal
    user_id, and sets a session cookie. Falls back to legacy auth if
    Supabase is not configured.
    """
    settings = _get_settings(request)
    db = _get_db(request)

    supabase_integration = SupabaseAuthIntegration(
        supabase_url=getattr(settings, "SUPABASE_URL", ""),
        jwt_secret=getattr(settings, "SUPABASE_JWT_SECRET", ""),
        jwks_url=getattr(settings, "SUPABASE_JWKS_URL", ""),
    )
    if not supabase_integration.enabled:
        return err(
            "not_configured",
            "Supabase authentication is not configured",
            501,
        )

    body = await request.json()
    access_token = body.get("access_token")
    if not access_token:
        return err("missing_token", "Supabase access token required", 400)

    user_repo = UserRepository(db)
    supabase_service = SupabaseAuthService(user_repo, supabase_integration)
    user = await supabase_service.authenticate(access_token)
    if user is None:
        return err("auth_failed", "Invalid Supabase session", 401)

    session_repo = SessionRepository(db)
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
    return ok({"session_token": session_token, "user": user})


@router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    return ok({
        "user": {
            k: v for k, v in user.items() if k not in {"_id", "_session_token"}
        }
    })


@router.get("/auth/identity-audit")
async def identity_audit(request: Request, user=Depends(get_current_user)):
    service = IdentityRepairService(_get_db(request))
    return ok(await service.audit(user))


@router.post("/auth/repair-identity")
async def repair_identity(request: Request, user=Depends(get_current_user)):
    service = IdentityRepairService(_get_db(request))
    result = await service.repair(user)
    public_user = result.get("user") or {}
    result["user"] = {
        k: v for k, v in public_user.items() if k not in {"_id", "_session_token"}
    }
    return ok(result)


@router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        db = _get_db(request)
        session_repo = SessionRepository(db)
        await session_repo.delete_session(token)
    response.delete_cookie("session_token", path="/")
    return ok({"logged_out": True})
