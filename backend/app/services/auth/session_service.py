from __future__ import annotations

from typing import Any, Dict, Optional

from app.integrations.google_oauth import GoogleOAuthIntegration
from app.repositories.sessions import SessionRepository
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.auth.user_service import UserService


class SessionService:
    def __init__(
        self,
        session_repo: SessionRepository,
        oauth_state_service: OAuthStateService,
        user_service: UserService,
    ):
        self._session_repo = session_repo
        self._oauth_state_service = oauth_state_service
        self._user_service = user_service

    async def create_session(self, user_id: str) -> str:
        return await self._session_repo.create_session(user_id)

    async def destroy_session(self, token: str) -> None:
        await self._session_repo.delete_session(token)

    async def login_with_google(
        self,
        code: str,
        state: str,
        google_oauth: GoogleOAuthIntegration,
    ) -> Optional[Dict[str, Any]]:
        user_id_from_state = await self._oauth_state_service.consume(
            state, "login"
        )
        if user_id_from_state is None:
            return None

        tokens = await google_oauth.exchange_code(code)
        if tokens is None:
            return None

        access_token = tokens.get("access_token")
        google_user = await google_oauth.get_user_info(access_token)
        if google_user is None:
            return None

        user = await self._user_service.find_or_create_google_user(
            email=google_user["email"],
            name=google_user.get("name", ""),
            picture=google_user.get("picture", ""),
        )

        session_token = await self._session_repo.create_session(
            user["user_id"]
        )

        return {"session_token": session_token, "user": user}

    async def login_dev(self) -> Optional[Dict[str, Any]]:
        user = await self._user_service.create_dev_user()
        session_token = await self._session_repo.create_session(
            user["user_id"]
        )
        return {"session_token": session_token, "user": user}
