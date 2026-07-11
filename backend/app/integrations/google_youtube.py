from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Optional

import httpx

from app.core.time import iso, now_utc
from app.repositories.youtube import YouTubeCredentialRepository


class YouTubeAPIError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 502,
        clear_credentials: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.clear_credentials = clear_credentials


class YouTubeAPI:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""
        self.base = "https://www.googleapis.com/youtube/v3"

    @staticmethod
    def _google_error_details(resp):
        try:
            payload = resp.json()
        except Exception:
            return resp.text[:300], []

        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return resp.text[:300], []
        message = error.get("message") or resp.text[:300]
        reasons = [
            e.get("reason", "")
            for e in error.get("errors", [])
            if isinstance(e, dict)
        ]
        status = error.get("status")
        if status:
            reasons.append(str(status))
        return message, [r for r in reasons if r]

    @classmethod
    def _raise_for_youtube_error(cls, resp) -> None:
        if 200 <= resp.status_code < 300:
            return

        message, reasons = cls._google_error_details(resp)
        reason_text = " ".join(reasons + [message]).lower()

        if resp.status_code == 401:
            raise YouTubeAPIError(
                "youtube_reconnect_required",
                "YouTube access expired. Reconnect YouTube in Settings.",
                401,
                clear_credentials=True,
            )

        if resp.status_code == 403:
            if "quota" in reason_text or "ratelimit" in reason_text:
                raise YouTubeAPIError(
                    "youtube_quota_exceeded",
                    "YouTube API quota was exceeded. Try again later.",
                    429,
                )
            if (
                "insufficient" in reason_text
                or "permission" in reason_text
                or "scope" in reason_text
            ):
                raise YouTubeAPIError(
                    "youtube_reconnect_required",
                    "YouTube permission is missing or expired. Reconnect YouTube in Settings.",
                    403,
                    clear_credentials=True,
                )
            if "forbidden" in reason_text or "private" in reason_text:
                raise YouTubeAPIError(
                    "youtube_playlist_forbidden",
                    "This playlist is private or your YouTube account cannot access it.",
                    403,
                )

        if resp.status_code == 404:
            raise YouTubeAPIError(
                "not_found", "Playlist not found on YouTube.", 404
            )

        if resp.status_code == 429 or resp.status_code >= 500:
            raise YouTubeAPIError(
                "youtube_retry_later",
                "YouTube is temporarily unavailable. Try again in a moment.",
                503,
            )

        raise YouTubeAPIError(
            "youtube_api_failed",
            f"YouTube API failed: {message}",
            502,
        )

    async def _get(self, path, params, token):
        request_params = dict(params)
        headers = {}
        if self.api_key:
            request_params["key"] = self.api_key
        else:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base}{path}",
                    params=request_params,
                    headers=headers,
                )
                self._raise_for_youtube_error(resp)
                return resp
        except httpx.RequestError as exc:
            raise YouTubeAPIError(
                "youtube_retry_later",
                f"Could not reach YouTube. Try again in a moment. ({exc.__class__.__name__})",
                503,
            )

    async def fetch_playlist_meta(self, pid: str, token: str):
        resp = await self._get(
            "/playlists",
            {"part": "snippet,contentDetails", "id": pid},
            token,
        )
        items = resp.json().get("items") or []
        if not items:
            return None
        return {
            "snippet": items[0]["snippet"],
            "item_count": items[0]["contentDetails"]["itemCount"],
        }

    async def fetch_playlist_items(self, pid: str, token: str) -> list:
        videos = []
        page_token = None
        while True:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": pid,
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token
            resp = await self._get("/playlistItems", params, token)
            page = resp.json()
            for it in page.get("items", []):
                videos.append({
                    "youtube_video_id": it["contentDetails"]["videoId"],
                    "title": it["snippet"]["title"],
                    "position": it["snippet"]["position"],
                })
            page_token = page.get("nextPageToken")
            if not page_token:
                return videos

    async def fetch_video_durations(self, video_ids: list, token: str) -> dict:
        from app.services.playlists.commands import iso8601_to_seconds

        out = {}
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            resp = await self._get(
                "/videos",
                {"part": "contentDetails", "id": ",".join(chunk)},
                token,
            )
            for it in resp.json().get("items", []):
                out[it["id"]] = iso8601_to_seconds(
                    it["contentDetails"]["duration"]
                )
        return out


class YouTubeTokenManager:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    async def get_token(
        self, user_id: str, repo: YouTubeCredentialRepository
    ) -> Optional[str]:
        doc = await repo.find(user_id)
        if not doc:
            return None
        token = doc.get("access_token", "")
        refresh_token = doc.get("refresh_token", "")
        expiry_str = doc.get("expiry")

        if not token:
            return None

        if expiry_str:
            from datetime import datetime, timezone

            expiry = datetime.fromisoformat(expiry_str).replace(
                tzinfo=timezone.utc
            )
            if now_utc() >= expiry:
                if not refresh_token:
                    return None
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.post(
                            "https://oauth2.googleapis.com/token",
                            data={
                                "client_id": self.client_id,
                                "client_secret": self.client_secret,
                                "refresh_token": refresh_token,
                                "grant_type": "refresh_token",
                            },
                            timeout=15,
                        )
                        r.raise_for_status()
                        data = r.json()
                        token = data["access_token"]
                        new_expiry = now_utc() + timedelta(
                            seconds=data.get("expires_in", 3600)
                        )
                        await repo.update_token(user_id, token, iso(new_expiry))
                except Exception:
                    import logging

                    logging.warning(
                        f"YouTube token refresh failed for {user_id}"
                    )
                    await repo.delete(user_id)
                    return None
        return token

    async def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
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
                if r.status_code != 200:
                    return None
                return r.json()
        except Exception:
            return None

    async def revoke_token(self, refresh_token: str) -> None:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": refresh_token},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    timeout=10,
                )
        except Exception:
            pass
