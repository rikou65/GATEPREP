from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.time import iso, now_utc


class YouTubeCredentialRepository:
    def __init__(self, db):
        self._db = db

    async def find(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.youtube_credentials.find_one(
            {"user_id": user_id}, {"_id": 0}
        )

    async def upsert(self, user_id: str, data: Dict[str, Any]) -> None:
        await self._db.youtube_credentials.update_one(
            {"user_id": user_id},
            {
                "$set": data,
                "$setOnInsert": {"connected_at": iso(now_utc())},
            },
            upsert=True,
        )

    async def delete(self, user_id: str) -> None:
        await self._db.youtube_credentials.delete_one(
            {"user_id": user_id}
        )

    async def update_token(
        self, user_id: str, access_token: str, expiry: str
    ) -> None:
        await self._db.youtube_credentials.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "access_token": access_token,
                    "expiry": expiry,
                    "updated_at": iso(now_utc()),
                }
            },
        )
