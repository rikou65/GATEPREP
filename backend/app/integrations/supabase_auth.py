from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import jwt

from app.core.logging import logger


class SupabaseAuthIntegration:
    """Verifies Supabase JWTs and extracts user identity.

    Supports both asymmetric (JWKS — ES256/RS256) and symmetric (JWT secret)
    verification. Tries JWKS first, falls back to JWT secret.
    Gracefully disables itself when no Supabase config is provided.
    """

    def __init__(
        self,
        supabase_url: str = "",
        jwt_secret: str = "",
        jwks_url: str = "",
    ):
        self._supabase_url = supabase_url
        self._jwt_secret = jwt_secret
        self._jwks_url = jwks_url or (
            f"{supabase_url}/auth/v1/.well-known/jwks.json"
            if supabase_url
            else ""
        )
        self._jwks_cache: Optional[list] = None

        self.enabled = bool(
            supabase_url and (jwt_secret or self._jwks_url)
        )

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a Supabase JWT and return the decoded payload.

        Tries asymmetric (JWKS) first, then symmetric (JWT secret).
        Returns None if the token is invalid, expired, or Supabase is
        not configured.
        """
        if not self.enabled:
            return None

        if self._jwks_url:
            payload = await self._verify_asymmetric(token)
            if payload is not None:
                return payload

        if self._jwt_secret:
            return self._verify_symmetric(token)

        return None

    def _verify_symmetric(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Supabase JWT expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Supabase JWT invalid: {e}")
        return None

    async def _verify_asymmetric(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            if self._jwks_cache is None:
                await self._fetch_jwks()

            if not self._jwks_cache:
                return None

            from jwt import PyJWKClient

            jwk_client = PyJWKClient(self._jwks_url, cache_keys=True)
            signing_key = jwk_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[
                    "ES256", "ES384", "ES512",
                    "RS256", "RS384", "RS512",
                    "PS256", "PS384", "PS512",
                ],
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Supabase JWT expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Supabase JWT invalid: {e}")
        except Exception as e:
            logger.warning(f"Supabase JWT verification error: {e}")
        return None

    async def _fetch_jwks(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self._jwks_url, timeout=10)
                if resp.status_code == 200:
                    self._jwks_cache = resp.json().get("keys", [])
                else:
                    logger.warning(
                        f"Failed to fetch Supabase JWKS: {resp.status_code}"
                    )
        except Exception as e:
            logger.warning(f"Supabase JWKS fetch error: {e}")

    def extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standard user fields from a verified Supabase JWT payload."""
        return {
            "supabase_user_id": payload.get("sub", ""),
            "email": payload.get("email", ""),
            "name": payload.get("user_metadata", {}).get(
                "full_name", payload.get("user_metadata", {}).get("name", "")
            ),
            "picture": payload.get("user_metadata", {}).get("avatar_url", ""),
            "email_verified": payload.get("email_verified", False),
        }
