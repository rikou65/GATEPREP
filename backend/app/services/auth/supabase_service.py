from __future__ import annotations

from typing import Any, Dict, Optional

from app.integrations.supabase_auth import SupabaseAuthIntegration
from app.repositories.users import UserRepository
from app.services.auth.identity_repair_service import IdentityRepairService


class SupabaseAuthService:
    """Maps Supabase-authenticated users to internal user_id.

    On first Supabase login, performs a safe email-based migration:
    - Only auto-links if Supabase email is verified.
    - Preserves existing internal user_id and Drive/YouTube tokens.
    - Creates a fresh user if no match exists.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        supabase_integration: SupabaseAuthIntegration,
    ):
        self._user_repo = user_repo
        self._supabase = supabase_integration

    @property
    def enabled(self) -> bool:
        return self._supabase.enabled

    async def resolve(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a Supabase JWT and return the EXISTING internal user.

        Lookup-only — does NOT auto-link or create users. Used by
        ``get_current_user`` on every authenticated request so that read
        endpoints never mutate the ``users`` collection as a side effect.
        Auto-link/create happens only in ``authenticate``, which is called
        from the explicit ``POST /auth/supabase-session`` flow.
        Returns None if Supabase is not configured, the token is invalid,
        or no mapped internal user exists yet.
        """
        if not self._supabase.enabled:
            return None

        payload = await self._supabase.verify_token(token)
        if payload is None:
            return None

        supabase_info = self._supabase.extract_user_info(payload)
        supabase_user_id = supabase_info["supabase_user_id"]
        return await self._user_repo.find_by_supabase_id(supabase_user_id)

    async def authenticate(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a Supabase JWT and return the internal user.

        Used by ``POST /auth/supabase-session`` to mint a backend session.
        If the user does not yet have a mapping, attempts to auto-link
        by verified email. Returns None if Supabase is not configured or
        the token is invalid.
        """
        if not self._supabase.enabled:
            return None

        payload = await self._supabase.verify_token(token)
        if payload is None:
            return None

        supabase_info = self._supabase.extract_user_info(payload)
        supabase_user_id = supabase_info["supabase_user_id"]
        email = supabase_info["email"]
        email_verified = supabase_info["email_verified"]

        existing = await self._user_repo.find_by_supabase_id(
            supabase_user_id
        )
        if existing:
            if email_verified:
                repair_service = IdentityRepairService(self._user_repo.db)
                audit = await repair_service.audit(existing)
                if not audit.get("current_is_canonical"):
                    result = await repair_service.repair(existing)
                    return result.get("user") or existing
            return existing

        matched = await self._try_auto_link(
            email, supabase_user_id, email_verified
        )
        if matched:
            return matched

        if not email_verified and await self._user_repo.find_by_email(email):
            return None

        user = await self._user_repo.create_supabase_user(
            supabase_user_id=supabase_user_id,
            email=email,
            name=supabase_info["name"],
            picture=supabase_info["picture"],
            email_verified=email_verified,
        )
        return user

    async def _try_auto_link(
        self, email: str, supabase_user_id: str, email_verified: bool
    ) -> Optional[Dict[str, Any]]:
        if not email_verified:
            return None

        existing = await self._user_repo.find_by_email(email)
        if existing is None:
            return None

        await self._user_repo.link_supabase_identity(
            existing["user_id"], supabase_user_id
        )
        return await self._user_repo.find_by_user_id(existing["user_id"])
