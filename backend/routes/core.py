from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response

import secrets
import httpx
from shared import ADMIN_EMAILS, async_get, db, err, get_current_user, iso, logger, new_id, now_utc, ok, _migrate_per_user_content, settings

router = APIRouter()


@router.post("/auth/dev-login")
async def dev_login(response: Response):
    """Bypass external OAuth for local development."""
    user_id = "demo_user_123"
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "email": "demo@example.com",
            "name": "Demo Student",
            "is_admin": True,
            "updated_at": iso(now_utc())
        }, "$setOnInsert": {"created_at": iso(now_utc())}},
        upsert=True
    )
    
    token = secrets.token_urlsafe(32)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": iso(now_utc() + timedelta(days=7)),
        "created_at": iso(now_utc())
    })
    
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=604800, # 7 days
        samesite="lax",
    )
    user = {
        "user_id": user_id,
        "email": "demo@example.com",
        "name": "Demo Student",
        "is_admin": True,
        "picture": ""
    }
    return ok({"session_token": token, "user": user})


@router.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    code = body.get("code")
    if not code:
        return err("missing_code", "Authorization code required", 400)
    
    try:
        # 1. Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_LOGIN_REDIRECT_URI,
                },
                timeout=15
            )
            if token_resp.status_code != 200:
                logger.error(f"Google token exchange failed: {token_resp.status_code} {token_resp.text}")
                return err("auth_failed", f"Google token exchange failed: {token_resp.text}", 401)
            
            tokens = token_resp.json()
            access_token = tokens.get("access_token")
            
            # 2. Get user info from Google
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            user_resp.raise_for_status()
            google_user = user_resp.json()
            
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        return err("auth_failed", f"Failed to authenticate with Google: {str(e)}", 401)

    email = google_user["email"]
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": google_user.get("name"), "picture": google_user.get("picture", "")}},
        )
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    else:
        user_id = new_id("user")
        # First user is admin
        is_admin = (await db.users.count_documents({})) == 0
        user = {
            "user_id": user_id,
            "email": email,
            "name": google_user.get("name"),
            "picture": google_user.get("picture", ""),
            "is_admin": is_admin,
            "created_at": iso(now_utc()),
        }
        await db.users.insert_one(dict(user))
        user.pop("_id", None)

    session_token = secrets.token_urlsafe(32)
    expires_at = now_utc() + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token, "expires_at": iso(expires_at),
        "created_at": iso(now_utc()),
    })
    
    response.set_cookie(
        key="session_token", value=session_token, httponly=True,
        secure=False, samesite="lax", path="/", max_age=7 * 24 * 3600,
    )
    
    return ok({"user": user})


@router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    return ok({"user": {k: v for k, v in user.items() if k != "_id"}})


@router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return ok({"logged_out": True})


@router.get("/subjects")
async def list_subjects():
    docs = await db.subjects.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return ok(docs)


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: str):
    s = await db.subjects.find_one({"subject_id": subject_id}, {"_id": 0})
    if not s:
        return err("not_found", "Subject not found", 404)
    return ok(s)


@router.get("/subjects/{subject_id}/topics")
async def list_topics(subject_id: str):
    docs = await db.topics.find({"subject_id": subject_id}, {"_id": 0}).sort("order", 1).to_list(500)
    return ok(docs)


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    t = await db.topics.find_one({"topic_id": topic_id}, {"_id": 0})
    if not t:
        return err("not_found", "Topic not found", 404)
    s = await db.subjects.find_one({"subject_id": t["subject_id"]}, {"_id": 0})
    t["subject"] = s
    return ok(t)
