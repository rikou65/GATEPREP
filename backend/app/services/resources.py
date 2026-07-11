from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.core.constants import DRIVE_ROOT_NAME
from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.integrations.google_drive import GoogleDriveIntegration
from app.repositories.resources import (
    DriveCredentialRepository,
    ResourceNoteRepository,
    ResourceRepository,
)
from app.repositories.subjects import SubjectRepository


def normalize_pages(raw) -> List[Dict[str, Any]]:
    seen: Dict[int, str] = {}
    for item in raw or []:
        try:
            if isinstance(item, dict):
                p = int(item.get("page", 0))
                lbl = str(item.get("label", "") or "")
            else:
                p = int(item)
                lbl = ""
        except (ValueError, TypeError):
            continue
        if p <= 0:
            continue
        if p in seen and not lbl:
            continue
        seen[p] = lbl
    return [{"page": p, "label": seen[p]} for p in sorted(seen.keys())]


def resource_notes_view(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not doc:
        return {"content": "", "important_pages": []}
    return {
        "content": doc.get("content", "") or "",
        "important_pages": normalize_pages(doc.get("important_pages")),
        "updated_at": doc.get("updated_at"),
    }


class ResourceService:
    def __init__(
        self,
        res_repo: ResourceRepository,
        note_repo: ResourceNoteRepository,
        drive_repo: DriveCredentialRepository,
        subject_repo: SubjectRepository,
        drive_integration: GoogleDriveIntegration,
    ):
        self._res_repo = res_repo
        self._note_repo = note_repo
        self._drive_repo = drive_repo
        self._subject_repo = subject_repo
        self._drive = drive_integration

    async def create(self, user_id: str, subject_id: str, resource_type: str, title: str, external_url: str, file_size: int) -> Dict[str, Any]:
        doc = {
            "resource_id": new_id("res"),
            "user_id": user_id,
            "subject_id": subject_id,
            "resource_type": resource_type,
            "title": title,
            "external_url": external_url or "",
            "file_size": file_size or 0,
            "created_at": iso(now_utc()),
            "source": "external",
        }
        await self._res_repo.create(doc)
        return doc

    async def list(self, user_id: str, subject_id: Optional[str] = None, resource_type: Optional[str] = None) -> list:
        return await self._res_repo.list(user_id, subject_id, resource_type)

    async def delete(self, user_id: str, resource_id: str) -> int:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if res and res.get("drive_file_id"):
            service = await self._drive.build_service(user_id, self._drive_repo)
            if service:
                try:
                    service.files().delete(fileId=res["drive_file_id"]).execute()
                except Exception:
                    pass
        deleted = await self._res_repo.delete(resource_id, user_id)
        await self._note_repo.delete(resource_id, user_id)
        return deleted

    async def get_notes(self, resource_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        doc = await self._note_repo.find(resource_id, user_id)
        return resource_notes_view(doc)

    async def save_notes(self, resource_id: str, user_id: str, content: Optional[str], important_pages: Optional[list]) -> Optional[str]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        data = {}
        if content is not None:
            data["content"] = content
        if important_pages is not None:
            data["important_pages"] = normalize_pages(important_pages)
        await self._note_repo.upsert(resource_id, user_id, data)
        doc = await self._note_repo.find(resource_id, user_id)
        return resource_notes_view(doc)

    async def sync_drive(self, user_id: str) -> Dict[str, Any]:
        service = await self._drive.build_service(user_id, self._drive_repo)
        if not service:
            return {"synced": 0, "skipped": 0, "error": "drive_not_connected"}

        subjects = await self._subject_repo.list_all()
        subj_by_name = {s["name"].lower(): s["subject_id"] for s in subjects}

        existing_ids = await self._res_repo.find_by_drive_ids(user_id)
        folder_mime = "application/vnd.google-apps.folder"
        root_id = GoogleDriveIntegration.find_folder(
            service, DRIVE_ROOT_NAME, None
        )
        if not root_id:
            return {"synced": 0, "skipped": 0, "error": "no_gateprep_folder"}

        synced = 0
        skipped = 0
        unknown_subjects = []

        type_folders = GoogleDriveIntegration.list_children(
            service, root_id, mime_type=folder_mime
        )
        for tf in type_folders:
            resource_type = tf["name"]
            subj_folders = GoogleDriveIntegration.list_children(
                service, tf["id"], mime_type=folder_mime
            )
            for sf in subj_folders:
                subj_name = sf["name"]
                subject_id = subj_by_name.get(subj_name.lower())
                if not subject_id:
                    if subj_name not in unknown_subjects:
                        unknown_subjects.append(subj_name)
                    continue
                files = GoogleDriveIntegration.list_children(service, sf["id"])
                for f in files:
                    if f["id"] in existing_ids:
                        skipped += 1
                        continue
                    doc = {
                        "resource_id": new_id("res"),
                        "user_id": user_id,
                        "subject_id": subject_id,
                        "resource_type": resource_type,
                        "title": f.get("name", "Untitled"),
                        "filename": f.get("name", ""),
                        "mime_type": f.get("mimeType", ""),
                        "file_size": int(f.get("size", 0) or 0),
                        "drive_file_id": f["id"],
                        "external_url": f.get("webViewLink", ""),
                        "source": "drive",
                        "created_at": f.get("createdTime") or iso(now_utc()),
                        "synced_at": iso(now_utc()),
                    }
                    await self._res_repo.create(doc)
                    existing_ids.add(f["id"])
                    synced += 1

        return {
            "synced": synced,
            "skipped": skipped,
            "unknown_subjects": unknown_subjects,
        }

    async def handle_drive_callback(self, user_id: str, code: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self._drive._client_id,
                        "client_secret": self._drive._client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self._drive._redirect_uri,
                    },
                    timeout=15,
                )
                if token_resp.status_code != 200:
                    return False

                tokens = token_resp.json()
                about_resp = await client.get(
                    "https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)",
                    headers={
                        "Authorization": f"Bearer {tokens['access_token']}"
                    },
                    timeout=10,
                )
                drive_email = ""
                if about_resp.status_code == 200:
                    drive_email = (
                        about_resp.json()
                        .get("user", {})
                        .get("emailAddress", "")
                    )

            expiry_iso = None
            if "expires_in" in tokens:
                expiry_dt = now_utc() + timedelta(seconds=tokens["expires_in"])
                expiry_iso = iso(expiry_dt)

            set_data = {
                "user_id": user_id,
                "access_token": tokens.get("access_token"),
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": tokens.get("scope", "").split(" "),
                "expiry": expiry_iso,
                "drive_email": drive_email,
                "updated_at": iso(now_utc()),
            }
            if tokens.get("refresh_token"):
                set_data["refresh_token"] = tokens["refresh_token"]

            await self._drive_repo.upsert(user_id, set_data)
            return True
        except Exception:
            return False
