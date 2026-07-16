from __future__ import annotations

from typing import Any, Dict, Optional

from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository


class UserService:
    def __init__(
        self, user_repo: UserRepository, session_repo: SessionRepository
    ):
        self._user_repo = user_repo
        self._session_repo = session_repo

    async def find_or_create_google_user(
        self, email: str, name: str, picture: str
    ) -> Dict[str, Any]:
        user = await self._user_repo.upsert_google_user(email, name, picture)
        return user

    async def create_dev_user(self) -> Dict[str, Any]:
        user = await self._user_repo.upsert_dev_user()
        return user

    async def find_by_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        return await self._user_repo.find_by_session_token(token)

    async def find_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._user_repo.find_by_user_id(user_id)
