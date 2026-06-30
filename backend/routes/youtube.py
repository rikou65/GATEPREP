from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request, Response
import httpx

from shared import db, err, get_current_user, iso, logger, new_id, now_utc, ok, settings

router = APIRouter()

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


async def _get_youtube_token(user_id: str) -> str | None:
    doc = await db.youtube_credentials.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return None
    token = doc.get("access_token", "")
    refresh_token = doc.get("refresh_token", "")
    expiry = datetime.fromisoformat(doc["expiry"]).replace(tzinfo=timezone.utc) if doc.get("expiry") else None
    if not token:
        return None
    if expiry and now_utc() >= expiry:
        if not refresh_token:
            return None
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=15,
                )
                r.raise_for_status()
                data = r.json()
                token = data["access_token"]
                new_expiry = now_utc() + timedelta(seconds=data.get("expires_in", 3600))
                await db.youtube_credentials.update_one(
                    {"user_id": user_id},
                    {"$set": {"access_token": token, "expiry": iso(new_expiry), "updated_at": iso(now_utc())}},
                )
        except Exception as e:
            logger.warning(f"YouTube token refresh failed for {user_id}: {e}")
            await db.youtube_credentials.delete_one({"user_id": user_id})
            return None
    return token


@router.get("/youtube/auth")
async def youtube_auth(user=Depends(get_current_user)):
    if not settings.GOOGLE_DRIVE_CLIENT_ID:
        return err("config", "Google API not configured", 500)
    params = {
        "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_YOUTUBE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(YT_SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": user["user_id"],
    }
    q = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    return ok({"authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{q}"})


@router.get("/youtube/callback")
async def youtube_callback(code: str = Query(...), state: str = Query(...)):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_YOUTUBE_REDIRECT_URI,
                },
                timeout=15,
            )
            if r.status_code != 200:
                logger.error(f"YouTube token exchange failed: {r.text}")
                frontend = settings.FRONTEND_URL or "http://localhost:3000"
                return Response(status_code=302, headers={"Location": f"{frontend}/settings?youtube=error"})
            tokens = r.json()
        expiry_iso = iso(now_utc() + timedelta(seconds=tokens.get("expires_in", 3600))) if "expires_in" in tokens else None
        set_data = {
            "user_id": state,
            "access_token": tokens.get("access_token"),
            "expiry": expiry_iso,
            "updated_at": iso(now_utc()),
        }
        if tokens.get("refresh_token"):
            set_data["refresh_token"] = tokens["refresh_token"]
        await db.youtube_credentials.update_one(
            {"user_id": state},
            {"$set": set_data, "$setOnInsert": {"connected_at": iso(now_utc())}},
            upsert=True,
        )
        frontend = settings.FRONTEND_URL or "http://localhost:3000"
        return Response(status_code=302, headers={"Location": f"{frontend}/settings?youtube=connected"})
    except Exception as e:
        logger.error(f"YouTube callback error: {e}")
        frontend = settings.FRONTEND_URL or "http://localhost:3000"
        return Response(status_code=302, headers={"Location": f"{frontend}/settings?youtube=error"})


@router.get("/youtube/status")
async def youtube_status(user=Depends(get_current_user)):
    doc = await db.youtube_credentials.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        return ok({"connected": False})
    return ok({"connected": True, "connected_at": doc.get("connected_at")})


@router.post("/youtube/disconnect")
async def youtube_disconnect(user=Depends(get_current_user)):
    doc = await db.youtube_credentials.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if doc and doc.get("refresh_token"):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": doc["refresh_token"]},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )
        except Exception as e:
            logger.warning(f"YouTube token revoke failed: {e}")
    await db.youtube_credentials.delete_one({"user_id": user["user_id"]})
    return ok({"disconnected": True})
