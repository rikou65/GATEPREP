from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Optional

from app.core.time import iso, now_utc


class SessionRepository:
    def __init__(self, db):
        self._db = db

    async def create_session(
        self, user_id: str, expires_in_days: int = 7
    ) -> str:
        token = secrets.token_urlsafe(32)
        await self._db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": token,
            "expires_at": iso(now_utc() + timedelta(days=expires_in_days)),
            "created_at": iso(now_utc()),
        })
        return token

    async def delete_session(self, token: str) -> None:
        await self._db.user_sessions.delete_one({"session_token": token})

    async def find_session(self, token: str) -> Optional[dict]:
        from datetime import datetime, timezone

        sess = await self._db.user_sessions.find_one(
            {"session_token": token}, {"_id": 0}
        )
        if not sess:
            return None
        exp = sess.get("expires_at")
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now_utc():
            return None
        return sess
