from __future__ import annotations

from typing import Optional

from app.repositories.oauth_states import OAuthStateRepository


class OAuthStateService:
    def __init__(self, repo: OAuthStateRepository):
        self._repo = repo

    async def generate(self, user_id: str, purpose: str) -> str:
        return await self._repo.create(user_id, purpose)

    async def consume(self, state: str, purpose: str) -> Optional[str]:
        return await self._repo.consume(state, purpose)
