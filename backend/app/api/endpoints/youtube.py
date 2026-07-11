from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.integrations.google_youtube import YouTubeTokenManager
from app.repositories.oauth_states import OAuthStateRepository
from app.repositories.youtube import YouTubeCredentialRepository
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.youtube import YT_SCOPES, YouTubeService

router = APIRouter()


def _build(request: Request):
    db = request.app.state.db
    settings = request.app.state.settings
    repo = YouTubeCredentialRepository(db)
    tm = YouTubeTokenManager(
        settings.GOOGLE_DRIVE_CLIENT_ID,
        settings.GOOGLE_DRIVE_CLIENT_SECRET,
        settings.GOOGLE_YOUTUBE_REDIRECT_URI,
    )
    svc = YouTubeService(repo, tm)
    oauth = OAuthStateService(OAuthStateRepository(db))
    return db, settings, repo, tm, svc, oauth


@router.get("/youtube/auth")
async def youtube_auth(
    request: Request,
    user=Depends(get_current_user),
):
    _, settings, _, _, _, oauth = _build(request)
    if not settings.GOOGLE_DRIVE_CLIENT_ID:
        return err("config", "Google API not configured", 500)
    state = await oauth.generate(user["user_id"], "youtube")
    params = {
        "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_YOUTUBE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(YT_SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    q = "&".join(
        f"{k}={urllib.parse.quote(v)}" for k, v in params.items()
    )
    return ok(
        {
            "authorization_url": (
                f"https://accounts.google.com/o/oauth2/v2/auth?{q}"
            )
        }
    )


@router.get("/youtube/callback")
async def youtube_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
):
    db, settings, _, _, svc, oauth = _build(request)
    frontend = settings.FRONTEND_URL or "http://localhost:3000"
    user_id = await oauth.consume(state, "youtube")
    if not user_id:
        return Response(
            status_code=302,
            headers={"Location": f"{frontend}/settings?youtube=error"},
        )
    success = await svc.handle_callback(user_id, code)
    if not success:
        return Response(
            status_code=302,
            headers={"Location": f"{frontend}/settings?youtube=error"},
        )
    return Response(
        status_code=302,
        headers={"Location": f"{frontend}/settings?youtube=connected"},
    )


@router.get("/youtube/status")
async def youtube_status(
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, svc, _ = _build(request)
    return ok(await svc.get_status(user["user_id"]))


@router.post("/youtube/disconnect")
async def youtube_disconnect(
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, svc, _ = _build(request)
    await svc.disconnect(user["user_id"])
    return ok({"disconnected": True})
