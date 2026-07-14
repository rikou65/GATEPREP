from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.migration import (
    SINGLETON_CREDENTIAL_COLLECTIONS,
    USER_OWNED_COLLECTIONS,
    MigrationRepository,
)
from app.repositories.users import UserRepository
from app.schemas.auth import CurrentUser


class IdentityRepairService:
    """Audits and repairs duplicate local users created during auth migration.

    Repair is intentionally non-destructive: duplicate user records are marked
    as merged, not deleted.
    """

    def __init__(self, db):
        self._users = UserRepository(db)
        self._migration = MigrationRepository(db)

    async def audit(self, current_user: CurrentUser) -> Dict[str, Any]:
        email = (current_user.email or "").strip().lower()
        candidates = (
            await self._users.list_by_email(email)
            if email
            else [current_user.model_dump()]
        )
        if not candidates:
            candidates = [current_user.model_dump()]

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

        canonical = self._choose_canonical(audited, current_user.user_id)
        return {
            "active_user_id": current_user.user_id,
            "email": email,
            "supabase_user_id": current_user.supabase_user_id,
            "canonical_user_id": canonical["user_id"],
            "current_is_canonical": canonical["user_id"] == current_user.user_id,
            "has_duplicate_email_users": len(candidates) > 1,
            "candidates": audited,
        }

    async def repair(
        self, current_user: CurrentUser, session_token: Optional[str] = None
    ) -> Dict[str, Any]:
        audit = await self.audit(current_user)
        canonical_user_id = audit["canonical_user_id"]
        current_user_id = current_user.user_id
        warnings: List[str] = []

        supabase_user_id = current_user.supabase_user_id
        if supabase_user_id:
            await self._users.move_supabase_identity(
                current_user_id, canonical_user_id, supabase_user_id
            )

        moved: Dict[str, int] = {}
        for candidate in audit["candidates"]:
            duplicate_user_id = candidate["user_id"]
            if duplicate_user_id == canonical_user_id:
                continue

            records_moved = await self._migration.migrate_user_owned_records(
                duplicate_user_id, canonical_user_id
            )
            for key, value in records_moved.items():
                moved[key] = moved.get(key, 0) + value

            cred_result = await self._migration.migrate_singleton_credentials(
                duplicate_user_id, canonical_user_id
            )
            for key, value in cred_result["moved"].items():
                moved[key] = moved.get(key, 0) + value
            warnings.extend(cred_result["warnings"])

            await self._migration.mark_user_merged(
                duplicate_user_id, canonical_user_id
            )

        if session_token:
            await self._migration.repoint_session_token(
                session_token, canonical_user_id
            )

        repaired_user = await self._users.find_by_user_id(canonical_user_id)
        audit_user = CurrentUser(**repaired_user) if repaired_user else current_user
        return {
            "canonical_user_id": canonical_user_id,
            "active_user_id_before_repair": current_user_id,
            "moved": moved,
            "warnings": warnings,
            "user": repaired_user,
            "audit": await self.audit(audit_user),
        }

    async def _counts_for_user(self, user_id: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for collection in USER_OWNED_COLLECTIONS + SINGLETON_CREDENTIAL_COLLECTIONS:
            counts[collection] = await self._migration.count_documents(
                collection, {"user_id": user_id}
            )
        return counts

    def _choose_canonical(
        self, candidates: List[Dict[str, Any]], current_user_id: str
    ) -> Dict[str, Any]:
        def score(candidate: Dict[str, Any]) -> tuple:
            counts = candidate.get("counts") or {}
            total = candidate.get("total_owned_records", 0)
            has_legacy_data = (
                1 if candidate.get("auth_provider") == "legacy_google" else 0
            )
            has_tokens = counts.get("drive_credentials", 0) + counts.get(
                "youtube_credentials", 0
            )
            is_current = 1 if candidate["user_id"] == current_user_id else 0
            return (total, has_tokens, has_legacy_data, is_current)

        return sorted(candidates, key=score, reverse=True)[0]
