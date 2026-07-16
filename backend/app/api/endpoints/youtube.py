from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import get_current_user
from app.api.providers import (
    get_oauth_state_service,
    get_settings,
    get_youtube_service,
)
from app.api.responses import err, ok
from app.schemas.auth import CurrentUser
from app.schemas.common import DisconnectedOut, Envelope, GoogleUrlOut, YouTubeStatusOut
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.youtube import YT_SCOPES, YouTubeService

router = APIRouter()


@router.get("/youtube/auth", response_model=Envelope[GoogleUrlOut])
async def youtube_auth(
    settings=Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
    oauth: OAuthStateService = Depends(get_oauth_state_service),
):
    if not settings.GOOGLE_DRIVE_CLIENT_ID:
        return err("config", "Google API not configured", 500)
    state = await oauth.generate(user.user_id, "youtube")
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
    q = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    return ok({"authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{q}"})


@router.get("/youtube/callback")
async def youtube_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    settings=Depends(get_settings),
    svc: YouTubeService = Depends(get_youtube_service),
    oauth: OAuthStateService = Depends(get_oauth_state_service),
):
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


@router.get("/youtube/status", response_model=Envelope[YouTubeStatusOut])
async def youtube_status(
    user: CurrentUser = Depends(get_current_user),
    svc: YouTubeService = Depends(get_youtube_service),
):
    return ok(await svc.get_status(user.user_id))


@router.post("/youtube/disconnect", response_model=Envelope[DisconnectedOut])
async def youtube_disconnect(
    user: CurrentUser = Depends(get_current_user),
    svc: YouTubeService = Depends(get_youtube_service),
):
    await svc.disconnect(user.user_id)
    return ok({"disconnected": True})
