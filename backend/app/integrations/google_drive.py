from __future__ import annotations

import asyncio
import io
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.core.config import Settings
from app.core.constants import DRIVE_SCOPES
from app.core.time import iso, now_utc
from app.repositories.resources import DriveCredentialRepository


class GoogleDriveIntegration:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._creds_cache: Dict[str, Credentials] = {}
        self._client_id = settings.GOOGLE_DRIVE_CLIENT_ID
        self._client_secret = settings.GOOGLE_DRIVE_CLIENT_SECRET
        self._redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI

    def _client_config(self) -> Dict[str, Any]:
        return {
            "web": {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._redirect_uri],
            }
        }

    def build_connect_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(DRIVE_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        encoded = "&".join(
            f"{k}={urllib.parse.quote(v)}" for k, v in params.items()
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{encoded}"

    async def _get_drive_creds(
        self, user_id: str, repo: DriveCredentialRepository
    ) -> Optional[Credentials]:
        cached = self._creds_cache.get(user_id)
        if cached and cached.valid:
            return cached

        doc = await repo.find(user_id)
        if not doc:
            self._creds_cache.pop(user_id, None)
            return None

        expiry = None
        if doc.get("expiry"):
            try:
                expiry = datetime.fromisoformat(doc["expiry"])
                if expiry.tzinfo:
                    expiry = expiry.astimezone(timezone.utc).replace(
                        tzinfo=None
                    )
            except Exception:
                expiry = None

        creds = Credentials(
            token=doc.get("access_token"),
            refresh_token=doc.get("refresh_token"),
            token_uri=doc.get(
                "token_uri", "https://oauth2.googleapis.com/token"
            ),
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=doc.get("scopes") or DRIVE_SCOPES,
            expiry=expiry,
        )

        if not creds.valid and creds.refresh_token:
            try:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as pool:
                    await loop.run_in_executor(
                        pool, lambda: creds.refresh(GoogleRequest())
                    )
                new_expiry = (
                    creds.expiry.replace(tzinfo=timezone.utc)
                    if creds.expiry
                    else None
                )
                await repo.update_token(
                    user_id,
                    creds.token,
                    iso(new_expiry) if new_expiry else None,
                )
            except Exception as e:
                import logging

                logging.warning(
                    f"Drive token refresh failed for {user_id}: {e}"
                )
                await repo.delete(user_id)
                self._creds_cache.pop(user_id, None)
                return None

        self._creds_cache[user_id] = creds
        return creds

    async def build_service(self, user_id: str, repo: DriveCredentialRepository):
        creds = await self._get_drive_creds(user_id, repo)
        if not creds:
            return None
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    @staticmethod
    def find_folder(service, name: str, parent_id: Optional[str]) -> Optional[str]:
        q_parts = [
            f"name='{name.replace(chr(39), chr(92)+chr(39))}'",
            "mimeType='application/vnd.google-apps.folder'",
            "trashed=false",
        ]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")
        res = (
            service.files()
            .list(
                q=" and ".join(q_parts),
                fields="files(id,name)",
                pageSize=10,
                spaces="drive",
            )
            .execute()
        )
        files = res.get("files", [])
        return files[0]["id"] if files else None

    @staticmethod
    def get_or_create_folder(
        service, name: str, parent_id: Optional[str] = None
    ) -> str:
        fid = GoogleDriveIntegration.find_folder(service, name, parent_id)
        if fid:
            return fid
        meta = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            meta["parents"] = [parent_id]
        created = service.files().create(body=meta, fields="id").execute()
        return created["id"]

    @staticmethod
    def list_children(
        service, parent_id: str, mime_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        q_parts = [f"'{parent_id}' in parents", "trashed=false"]
        if mime_type:
            q_parts.append(f"mimeType='{mime_type}'")
        else:
            q_parts.append(
                "mimeType!='application/vnd.google-apps.folder'"
            )
        out: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        while True:
            kwargs = {
                "q": " and ".join(q_parts),
                "fields": "nextPageToken, files(id,name,size,mimeType,webViewLink,createdTime,modifiedTime)",
                "pageSize": 200,
                "spaces": "drive",
            }
            if page_token:
                kwargs["pageToken"] = page_token
            res = service.files().list(**kwargs).execute()
            out.extend(res.get("files", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return out
