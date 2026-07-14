from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.time import iso, now_utc

_TOKEN_FIELDS = ("access_token", "refresh_token")


class ResourceRepository:
    def __init__(self, db):
        self._db = db

    async def find_by_id(self, resource_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.resources.find_one(
            {"resource_id": resource_id, "user_id": user_id}, {"_id": 0}
        )

    async def list(self, user_id: str, subject_id: Optional[str] = None, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {"user_id": user_id}
        if subject_id:
            q["subject_id"] = subject_id
        if resource_type:
            q["resource_type"] = resource_type
        return await self._db.resources.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)

    async def create(self, doc: Dict[str, Any]) -> None:
        await self._db.resources.insert_one(dict(doc))

    async def create_many(self, docs: List[Dict[str, Any]]) -> int:
        if not docs:
            return 0
        await self._db.resources.insert_many([dict(d) for d in docs])
        return len(docs)

    async def delete(self, resource_id: str, user_id: str) -> int:
        r = await self._db.resources.delete_one(
            {"resource_id": resource_id, "user_id": user_id}
        )
        return r.deleted_count

    async def find_by_drive_ids(self, user_id: str) -> set:
        existing = await self._db.resources.find(
            {"user_id": user_id, "drive_file_id": {"$exists": True, "$ne": None}},
            {"_id": 0, "drive_file_id": 1},
        ).to_list(10000)
        return {r["drive_file_id"] for r in existing if r.get("drive_file_id")}


class ResourceNoteRepository:
    def __init__(self, db):
        self._db = db

    async def find(self, resource_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.resource_notes.find_one(
            {"resource_id": resource_id, "user_id": user_id}, {"_id": 0}
        )

    async def upsert(self, resource_id: str, user_id: str, data: Dict[str, Any]) -> None:
        await self._db.resource_notes.update_one(
            {"resource_id": resource_id, "user_id": user_id},
            {
                "$set": {**data, "updated_at": iso(now_utc())},
                "$setOnInsert": {
                    "resource_id": resource_id,
                    "user_id": user_id,
                    "created_at": iso(now_utc()),
                },
            },
            upsert=True,
        )

    async def delete(self, resource_id: str, user_id: str) -> None:
        await self._db.resource_notes.delete_one(
            {"resource_id": resource_id, "user_id": user_id}
        )


class DriveCredentialRepository:
    def __init__(self, db):
        self._db = db

    async def find(self, user_id: str) -> Optional[Dict[str, Any]]:
        doc = await self._db.drive_credentials.find_one(
            {"user_id": user_id}, {"_id": 0}
        )
        if doc:
            for f in _TOKEN_FIELDS:
                if f in doc:
                    doc[f] = decrypt_secret(doc[f])
        return doc

    async def upsert(self, user_id: str, data: Dict[str, Any]) -> None:
        stored = dict(data)
        for f in _TOKEN_FIELDS:
            if f in stored:
                stored[f] = encrypt_secret(stored[f])
        await self._db.drive_credentials.update_one(
            {"user_id": user_id},
            {
                "$set": stored,
                "$setOnInsert": {"connected_at": iso(now_utc())},
            },
            upsert=True,
        )

    async def delete(self, user_id: str) -> None:
        await self._db.drive_credentials.delete_one({"user_id": user_id})

    async def update_token(
        self, user_id: str, access_token: str, expiry: Optional[str]
    ) -> None:
        await self._db.drive_credentials.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "access_token": encrypt_secret(access_token),
                    "expiry": expiry,
                    "updated_at": iso(now_utc()),
                }
            },
        )
