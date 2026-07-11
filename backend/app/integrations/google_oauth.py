from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.core.logging import logger


class GoogleOAuthIntegration:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def build_login_url(self, state: str) -> str:
        import urllib.parse

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        q = "&".join(
            f"{k}={urllib.parse.quote(v)}" for k, v in params.items()
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{q}"

    async def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.redirect_uri,
                    },
                    timeout=15,
                )
                if resp.status_code != 200:
                    logger.error(
                        f"Google token exchange failed: {resp.status_code} {resp.text}"
                    )
                    return None
                return resp.json()
        except Exception as e:
            logger.error(f"Google token exchange error: {e}")
            return None

    async def get_user_info(
        self, access_token: str
    ) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Google userinfo error: {e}")
            return None
