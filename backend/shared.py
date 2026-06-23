from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from config import Settings
from http_client import async_get, async_post

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

settings = Settings(_env_file=str(ROOT_DIR / ".env"))

mongo_url = settings.MONGO_URL
use_tls = "mongodb+srv://" in mongo_url or "replicaSet" in mongo_url or "ssl=true" in mongo_url.lower()
client = AsyncIOMotorClient(
    mongo_url, 
    tls=use_tls, 
    tlsAllowInvalidCertificates=True, 
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000
)
db = client[settings.DB_NAME]

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY or ""
ADMIN_EMAILS = settings.ADMIN_EMAILS_LIST
GOOGLE_DRIVE_CLIENT_ID = settings.GOOGLE_DRIVE_CLIENT_ID or ""
GOOGLE_DRIVE_CLIENT_SECRET = settings.GOOGLE_DRIVE_CLIENT_SECRET or ""
GOOGLE_DRIVE_REDIRECT_URI = settings.GOOGLE_DRIVE_REDIRECT_URI or ""

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_ROOT_NAME = "GATEPREP"
RESOURCE_TYPE_FOLDERS = ["Books", "Notes", "Question Banks", "PYQ Collections",
                          "Formula Sheets", "Reference Material"]

logger = logging.getLogger("gateos")
logging.basicConfig(level=logging.INFO)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def ok(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data}


def err(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "error": {"code": code, "message": message}},
    )


async def get_current_user(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session")
    exp = sess.get("expires_at")
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _migrate_per_user_content() -> None:
    first_user = await db.users.find_one({}, {"_id": 0, "user_id": 1}, sort=[("created_at", 1)])
    if not first_user:
        return
    uid = first_user["user_id"]
    await db.questions.update_many({"user_id": {"$exists": False}}, {"$set": {"user_id": uid}})
    await db.pyqs.update_many({"user_id": {"$exists": False}}, {"$set": {"user_id": uid}})
