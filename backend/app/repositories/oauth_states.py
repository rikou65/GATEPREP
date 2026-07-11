from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Optional

from app.core.constants import OAUTH_STATE_TTL_MINUTES
from app.core.time import iso, now_utc


class OAuthStateRepository:
    def __init__(self, db):
        self._db = db

    async def create(self, user_id: str, purpose: str) -> str:
        state = secrets.token_urlsafe(32)
        await self._db.oauth_states.insert_one({
            "state": state,
            "user_id": user_id,
            "purpose": purpose,
            "expires_at": iso(now_utc() + timedelta(minutes=OAUTH_STATE_TTL_MINUTES)),
            "used": False,
        })
        return state

    async def consume(self, state: str, purpose: str) -> Optional[str]:
        doc = await self._db.oauth_states.find_one_and_update(
            {
                "state": state,
                "purpose": purpose,
                "used": False,
                "expires_at": {"$gt": iso(now_utc())},
            },
            {"$set": {"used": True}},
            projection={"user_id": 1},
        )
        return doc["user_id"] if doc else None

    async def ensure_index(self) -> None:
        try:
            await self._db.oauth_states.create_index(
                "expires_at", expireAfterSeconds=0
            )
        except Exception:
            pass
