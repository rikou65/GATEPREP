from __future__ import annotations

from typing import Any, Dict, List

from app.core.security import hash_session_token
from app.core.time import iso, now_utc

USER_OWNED_COLLECTIONS = [
    "questions",
    "pyqs",
    "question_attempts",
    "mistakes",
    "resources",
    "resource_notes",
    "playlists",
    "video_progress",
    "video_notes",
    "staging_questions",
    "import_jobs",
    "topic_concepts",
]

SINGLETON_CREDENTIAL_COLLECTIONS = [
    "drive_credentials",
    "youtube_credentials",
]


class MigrationRepository:
    """Repository for the identity-repair migration flow.

    Consolidates all raw ``db[collection]`` access so the service layer
    never reaches into MongoDB by collection name.
    """

    def __init__(self, db):
        self._db = db

    # ── counts (audit) ─────────────────────────────────────────────────

    async def count_documents(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        return await self._db[collection].count_documents(filter_dict)

    # ── record migration (repair) ───────────────────────────────────────

    async def migrate_user_owned_records(
        self, from_user_id: str, to_user_id: str
    ) -> Dict[str, int]:
        moved: Dict[str, int] = {}
        migrated_at = iso(now_utc())
        for collection in USER_OWNED_COLLECTIONS:
            result = await self._db[collection].update_many(
                {"user_id": from_user_id},
                {
                    "$set": {
                        "user_id": to_user_id,
                        "migrated_from_user_id": from_user_id,
                        "migrated_at": migrated_at,
                    }
                },
            )
            if result.modified_count:
                moved[collection] = moved.get(collection, 0) + result.modified_count
        return moved

    async def migrate_singleton_credentials(
        self, from_user_id: str, to_user_id: str
    ) -> Dict[str, Any]:
        moved: Dict[str, int] = {}
        warnings: List[str] = []
        migrated_at = iso(now_utc())
        for collection in SINGLETON_CREDENTIAL_COLLECTIONS:
            duplicate_doc = await self._db[collection].find_one(
                {"user_id": from_user_id}
            )
            if not duplicate_doc:
                continue
            canonical_doc = await self._db[collection].find_one(
                {"user_id": to_user_id}
            )
            if canonical_doc:
                await self._db[collection].update_one(
                    {"_id": duplicate_doc["_id"]},
                    {
                        "$set": {
                            "duplicate_of_user_id": to_user_id,
                            "updated_at": migrated_at,
                        }
                    },
                )
                warnings.append(
                    f"{collection} already existed for canonical user; "
                    "duplicate credential preserved"
                )
                continue
            await self._db[collection].update_one(
                {"_id": duplicate_doc["_id"]},
                {
                    "$set": {
                        "user_id": to_user_id,
                        "migrated_from_user_id": from_user_id,
                        "migrated_at": migrated_at,
                    }
                },
            )
            moved[collection] = moved.get(collection, 0) + 1
        return {"moved": moved, "warnings": warnings}

    # ── user helpers ───────────────────────────────────────────────────

    async def mark_user_merged(
        self, duplicate_user_id: str, canonical_user_id: str
    ) -> None:
        await self._db.users.update_one(
            {"user_id": duplicate_user_id},
            {
                "$set": {
                    "merged_into_user_id": canonical_user_id,
                    "updated_at": iso(now_utc()),
                }
            },
        )

    async def repoint_session_token(
        self, session_token: str, user_id: str
    ) -> None:
        await self._db.user_sessions.update_one(
            {"session_token": hash_session_token(session_token)},
            {"$set": {"user_id": user_id}},
        )
