from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from app.core.time import iso, now_utc
from app.integrations.google_youtube import YouTubeTokenManager
from app.repositories.youtube import YouTubeCredentialRepository

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


class YouTubeService:
    def __init__(
        self,
        repo: YouTubeCredentialRepository,
        token_manager: YouTubeTokenManager,
    ):
        self._repo = repo
        self._token_manager = token_manager

    async def get_status(self, user_id: str) -> Dict[str, Any]:
        doc = await self._repo.find(user_id)
        if not doc:
            return {"connected": False}
        return {
            "connected": True,
            "connected_at": doc.get("connected_at"),
        }

    async def handle_callback(self, user_id: str, code: str) -> bool:
        tokens = await self._token_manager.exchange_code(code)
        if not tokens:
            return False
        expiry_iso = (
            iso(
                now_utc()
                + timedelta(seconds=tokens.get("expires_in", 3600))
            )
            if "expires_in" in tokens
            else None
        )
        set_data: Dict[str, Any] = {
            "user_id": user_id,
            "access_token": tokens.get("access_token"),
            "expiry": expiry_iso,
            "updated_at": iso(now_utc()),
        }
        if tokens.get("refresh_token"):
            set_data["refresh_token"] = tokens["refresh_token"]
        await self._repo.upsert(user_id, set_data)
        return True

    async def disconnect(self, user_id: str) -> None:
        doc = await self._repo.find(user_id)
        if doc and doc.get("refresh_token"):
            await self._token_manager.revoke_token(
                doc["refresh_token"]
            )
        await self._repo.delete(user_id)
