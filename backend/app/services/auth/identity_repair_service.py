from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.time import iso, now_utc
from app.repositories.users import UserRepository


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


class IdentityRepairService:
    """Audits and repairs duplicate local users created during auth migration.

    Repair is intentionally non-destructive: duplicate user records are marked
    as merged, not deleted.
    """

    def __init__(self, db):
        self._db = db
        self._users = UserRepository(db)

    async def audit(self, current_user: Dict[str, Any]) -> Dict[str, Any]:
        email = (current_user.get("email") or "").strip().lower()
        candidates = await self._users.list_by_email(email) if email else [current_user]
        if not candidates:
            candidates = [current_user]

        audited = []
        for user in candidates:
            counts = await self._counts_for_user(user["user_id"])
            audited.append({
                "user_id": user["user_id"],
                "email": user.get("email"),
                "auth_provider": user.get("auth_provider"),
                "supabase_user_id": user.get("supabase_user_id"),
                "merged_into_user_id": user.get("merged_into_user_id"),
                "counts": counts,
                "total_owned_records": sum(counts.values()),
            })

        canonical = self._choose_canonical(audited, current_user["user_id"])
        return {
            "active_user_id": current_user["user_id"],
            "email": email,
            "supabase_user_id": current_user.get("supabase_user_id"),
            "canonical_user_id": canonical["user_id"],
            "current_is_canonical": canonical["user_id"] == current_user["user_id"],
            "has_duplicate_email_users": len(candidates) > 1,
            "candidates": audited,
        }

    async def repair(self, current_user: Dict[str, Any]) -> Dict[str, Any]:
        audit = await self.audit(current_user)
        canonical_user_id = audit["canonical_user_id"]
        current_user_id = current_user["user_id"]
        warnings: List[str] = []

        supabase_user_id = current_user.get("supabase_user_id")
        if supabase_user_id:
            await self._users.move_supabase_identity(
                current_user_id, canonical_user_id, supabase_user_id
            )

        moved: Dict[str, int] = {}
        for candidate in audit["candidates"]:
            duplicate_user_id = candidate["user_id"]
            if duplicate_user_id == canonical_user_id:
                continue
            for collection in USER_OWNED_COLLECTIONS:
                result = await self._db[collection].update_many(
                    {"user_id": duplicate_user_id},
                    {
                        "$set": {
                            "user_id": canonical_user_id,
                            "migrated_from_user_id": duplicate_user_id,
                            "migrated_at": iso(now_utc()),
                        }
                    },
                )
                if result.modified_count:
                    moved[collection] = moved.get(collection, 0) + result.modified_count

            credential_result = await self._move_singleton_credentials(
                duplicate_user_id, canonical_user_id
            )
            moved.update({
                key: moved.get(key, 0) + value
                for key, value in credential_result["moved"].items()
            })
            warnings.extend(credential_result["warnings"])

            await self._db.users.update_one(
                {"user_id": duplicate_user_id},
                {
                    "$set": {
                        "merged_into_user_id": canonical_user_id,
                        "updated_at": iso(now_utc()),
                    }
                },
            )

        session_token = current_user.get("_session_token")
        if session_token:
            await self._db.user_sessions.update_one(
                {"session_token": session_token},
                {"$set": {"user_id": canonical_user_id}},
            )

        repaired_user = await self._users.find_by_user_id(canonical_user_id)
        return {
            "canonical_user_id": canonical_user_id,
            "active_user_id_before_repair": current_user_id,
            "moved": moved,
            "warnings": warnings,
            "user": repaired_user,
            "audit": await self.audit(repaired_user or current_user),
        }

    async def _counts_for_user(self, user_id: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for collection in USER_OWNED_COLLECTIONS + SINGLETON_CREDENTIAL_COLLECTIONS:
            counts[collection] = await self._db[collection].count_documents(
                {"user_id": user_id}
            )
        return counts

    def _choose_canonical(
        self, candidates: List[Dict[str, Any]], current_user_id: str
    ) -> Dict[str, Any]:
        def score(candidate: Dict[str, Any]) -> tuple:
            counts = candidate.get("counts") or {}
            total = candidate.get("total_owned_records", 0)
            has_legacy_data = 1 if candidate.get("auth_provider") == "legacy_google" else 0
            has_tokens = counts.get("drive_credentials", 0) + counts.get("youtube_credentials", 0)
            is_current = 1 if candidate["user_id"] == current_user_id else 0
            return (total, has_tokens, has_legacy_data, is_current)

        return sorted(candidates, key=score, reverse=True)[0]

    async def _move_singleton_credentials(
        self, duplicate_user_id: str, canonical_user_id: str
    ) -> Dict[str, Any]:
        moved: Dict[str, int] = {}
        warnings: List[str] = []
        for collection in SINGLETON_CREDENTIAL_COLLECTIONS:
            duplicate_doc = await self._db[collection].find_one(
                {"user_id": duplicate_user_id}
            )
            if not duplicate_doc:
                continue
            canonical_doc = await self._db[collection].find_one(
                {"user_id": canonical_user_id}
            )
            if canonical_doc:
                await self._db[collection].update_one(
                    {"_id": duplicate_doc["_id"]},
                    {
                        "$set": {
                            "duplicate_of_user_id": canonical_user_id,
                            "updated_at": iso(now_utc()),
                        }
                    },
                )
                warnings.append(
                    f"{collection} already existed for canonical user; duplicate credential preserved"
                )
                continue
            await self._db[collection].update_one(
                {"_id": duplicate_doc["_id"]},
                {
                    "$set": {
                        "user_id": canonical_user_id,
                        "migrated_from_user_id": duplicate_user_id,
                        "migrated_at": iso(now_utc()),
                    }
                },
            )
            moved[collection] = moved.get(collection, 0) + 1
        return {"moved": moved, "warnings": warnings}
