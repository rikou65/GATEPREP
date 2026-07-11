from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc


class UserRepository:
    def __init__(self, db):
        self._db = db

    async def link_supabase_identity(
        self, user_id: str, supabase_user_id: str
    ) -> None:
        now = iso(now_utc())
        await self._db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "auth_provider": "supabase",
                    "supabase_user_id": supabase_user_id,
                    "updated_at": now,
                }
            },
        )

    async def create_supabase_user(
        self,
        supabase_user_id: str,
        email: str,
        name: str = "",
        picture: str = "",
        email_verified: bool = False,
    ) -> Dict[str, Any]:
        now = iso(now_utc())
        user_id = new_id("user")
        user = {
            "user_id": user_id,
            "auth_provider": "supabase",
            "supabase_user_id": supabase_user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "email_verified": email_verified,
            "created_at": now,
            "updated_at": now,
        }
        await self._db.users.insert_one(dict(user))
        return user

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self._db.users.find_one({"email": email}, {"_id": 0})

    async def list_by_email(self, email: str) -> List[Dict[str, Any]]:
        return await self._db.users.find(
            {"email": email}, {"_id": 0}
        ).to_list(50)

    async def find_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.users.find_one({"user_id": user_id}, {"_id": 0})

    async def find_by_supabase_id(self, supabase_user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.users.find_one(
            {"supabase_user_id": supabase_user_id}, {"_id": 0}
        )

    async def move_supabase_identity(
        self,
        from_user_id: str,
        to_user_id: str,
        supabase_user_id: str,
    ) -> None:
        now = iso(now_utc())
        if from_user_id != to_user_id:
            await self._db.users.update_one(
                {"user_id": from_user_id},
                {
                    "$set": {
                        "merged_into_user_id": to_user_id,
                        "supabase_user_id_previous": supabase_user_id,
                        "updated_at": now,
                    },
                    "$unset": {"supabase_user_id": ""},
                },
            )
        await self._db.users.update_one(
            {"user_id": to_user_id},
            {
                "$set": {
                    "auth_provider": "supabase",
                    "supabase_user_id": supabase_user_id,
                    "email_verified": True,
                    "updated_at": now,
                }
            },
        )

    async def find_by_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        from app.core.time import now_utc

        sess = await self._db.user_sessions.find_one(
            {"session_token": token}, {"_id": 0}
        )
        if not sess:
            return None
        exp = sess.get("expires_at")
        if isinstance(exp, str):
            from datetime import datetime

            exp = datetime.fromisoformat(exp)
        if exp.tzinfo is None:
            from datetime import timezone

            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now_utc():
            return None
        user = await self.find_by_user_id(sess["user_id"])
        if not user:
            return None
        return user

    async def upsert_google_user(
        self, email: str, name: str, picture: str
    ) -> Dict[str, Any]:
        existing = await self.find_by_email(email)
        now = iso(now_utc())
        if existing:
            user_id = existing["user_id"]
            await self._db.users.update_one(
                {"user_id": user_id},
                {"$set": {"name": name, "picture": picture, "updated_at": now}},
            )
            user = await self.find_by_user_id(user_id)
        else:
            user_id = new_id("user")
            user = {
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "auth_provider": "legacy_google",
                "created_at": now,
                "updated_at": now,
            }
            await self._db.users.insert_one(dict(user))
        return user

    async def upsert_dev_user(self) -> Dict[str, Any]:
        user_id = "demo_user_123"
        now = iso(now_utc())
        await self._db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "email": "demo@example.com",
                    "name": "Demo Student",
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now, "auth_provider": "legacy_google"},
            },
            upsert=True,
        )
        user = await self.find_by_user_id(user_id)
        return user
