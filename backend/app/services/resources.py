from __future__ import annotations

import io
import os
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional

import httpx
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.core.constants import DRIVE_ROOT_NAME
from app.core.ids import new_id
from app.core.logging import logger
from app.core.time import iso, now_utc
from app.integrations.google_drive import GoogleDriveIntegration
from app.repositories.resources import (
    DriveCredentialRepository,
    ResourceNoteRepository,
    ResourceRepository,
)
from app.repositories.subjects import SubjectRepository
from app.services.auth.oauth_state_service import OAuthStateService


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
        oauth_state_service: OAuthStateService,
    ):
        self._res_repo = res_repo
        self._note_repo = note_repo
        self._drive_repo = drive_repo
        self._subject_repo = subject_repo
        self._drive = drive_integration
        self._oauth_state = oauth_state_service

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

    async def build_drive_connect_url(self, user_id: str) -> Optional[str]:
        if not self._drive._client_id:
            return None
        state = await self._oauth_state.generate(user_id, "drive")
        return self._drive.build_connect_url(state)

    async def handle_drive_oauth_callback(
        self, state: str, code: str
    ) -> bool:
        user_id = await self._oauth_state.consume(state, "drive")
        if not user_id:
            return False
        success = await self.handle_drive_callback(user_id, code)
        if not success:
            return False
        try:
            await self.sync_drive(user_id)
        except Exception:
            pass
        return True

    async def get_drive_status(self, user_id: str) -> Dict[str, Any]:
        doc = await self._drive_repo.find(user_id)
        if not doc:
            return {"connected": False}
        return {
            "connected": True,
            "user_id": user_id,
            "drive_email": doc.get("drive_email", ""),
            "connected_at": doc.get("connected_at"),
        }

    async def refresh_drive(self, user_id: str) -> Optional[Dict[str, Any]]:
        creds = await self._drive._get_drive_creds(user_id, self._drive_repo)
        if not creds:
            return None
        return {"refreshed": True, "valid": creds.valid}

    async def disconnect_drive(self, user_id: str) -> None:
        doc = await self._drive_repo.find(user_id)
        if doc and doc.get("refresh_token"):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": doc["refresh_token"]},
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
            except Exception:
                pass
        await self._drive_repo.delete(user_id)
        self._drive._creds_cache.pop(user_id, None)

    @staticmethod
    def _google_api_error(exc: Exception) -> Dict[str, Any]:
        if isinstance(exc, HttpError):
            status = getattr(exc.resp, "status", None)
            reason = getattr(exc.resp, "reason", "") or ""
            message = str(exc)
            try:
                data = exc.error_details
                if data:
                    first = data[0]
                    reason = first.get("reason") or reason
                    message = first.get("message") or message
            except Exception:
                pass
            return {"status": status, "reason": reason, "message": message}
        return {"status": None, "reason": "", "message": str(exc)}

    async def _drive_google_error(
        self, user_id: str, exc: Exception, stage: str
    ) -> Dict[str, Any]:
        details = self._google_api_error(exc)
        status = details["status"]
        reason = (details["reason"] or "").lower()
        message = details["message"] or "Google Drive request failed"

        logger.warning(
            "Drive %s failed for %s: status=%s reason=%s message=%s",
            stage,
            user_id,
            status,
            details["reason"],
            message,
            exc_info=True,
        )

        if status in (401, 403) or reason in {
            "autherror",
            "forbidden",
            "insufficientpermissions",
            "insufficientfilepermissions",
        }:
            await self._drive_repo.delete(user_id)
            self._drive._creds_cache.pop(user_id, None)
            return {
                "error": "drive_reconnect_required",
                "message": "Google Drive access needs to be reconnected in Settings.",
                "status_code": 401,
            }

        if status in (429, 500, 502, 503, 504) or reason in {
            "ratelimitexceeded",
            "userratelimitexceeded",
            "backenderror",
        }:
            return {
                "error": "drive_retry_later",
                "message": "Google Drive is temporarily unavailable. Try the upload again.",
                "status_code": 503,
            }

        return {
            "error": "drive_google_api_failed",
            "message": f"Google Drive folder setup failed: {message}",
            "status_code": 502,
        }

    async def upload_from_computer(
        self,
        user_id: str,
        subject_id: str,
        resource_type: str,
        title: Optional[str],
        original_filename: Optional[str],
        declared_mime: Optional[str],
        contents: bytes,
    ) -> Dict[str, Any]:
        try:
            service = await self._drive.build_service(user_id, self._drive_repo)
        except Exception as exc:
            logger.warning(
                "Drive upload failed while building Drive service for %s: %s",
                user_id,
                exc,
                exc_info=True,
            )
            return {
                "error": "drive_service_failed",
                "message": "Could not prepare Google Drive access. Reconnect Drive in Settings.",
                "status_code": 502,
            }
        if not service:
            logger.info(
                "Drive upload blocked because Drive is not connected for %s",
                user_id,
            )
            return {
                "error": "drive_not_connected",
                "message": "Connect Google Drive first",
                "status_code": 400,
            }

        subj = await self._subject_repo.find_by_id(subject_id)
        if not subj:
            logger.info(
                "Drive upload failed because subject was not found: user=%s subject=%s",
                user_id,
                subject_id,
            )
            return {
                "error": "not_found",
                "message": "Subject not found",
                "status_code": 404,
            }

        if not contents:
            return {"error": "empty_file", "message": "Empty file", "status_code": 400}
        if len(contents) > 200 * 1024 * 1024:
            return {
                "error": "too_large",
                "message": "File exceeds 200MB",
                "status_code": 413,
            }

        allowed_extensions = {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".doc",
            ".docx",
            ".txt",
            ".csv",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
        }
        allowed_mimes = {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }

        ext = (os.path.splitext((original_filename or "").strip())[1] or "").lower()
        if ext not in allowed_extensions:
            return {
                "error": "invalid_extension",
                "message": f"File extension '{ext}' not allowed",
                "status_code": 400,
            }
        mime_type = (declared_mime or "").lower()
        if mime_type not in allowed_mimes:
            return {
                "error": "invalid_mime",
                "message": f"Content type '{mime_type}' not allowed",
                "status_code": 400,
            }
        if ext == ".pdf" and contents[:4] != b"%PDF":
            return {
                "error": "invalid_pdf",
                "message": "File does not appear to be a valid PDF",
                "status_code": 400,
            }

        filename = (
            os.path.basename(original_filename or "file").replace("\x00", "")
        ) or "file"
        try:
            parent_id = GoogleDriveIntegration.get_or_create_folder(
                service, DRIVE_ROOT_NAME, None
            )
            type_id = GoogleDriveIntegration.get_or_create_folder(
                service, resource_type, parent_id
            )
            subject_folder_id = GoogleDriveIntegration.get_or_create_folder(
                service, subj["name"], type_id
            )
        except Exception as exc:
            return await self._drive_google_error(user_id, exc, "folder setup")

        media = MediaIoBaseUpload(
            io.BytesIO(contents), mimetype=mime_type, resumable=False
        )
        try:
            drive_file = (
                service.files()
                .create(
                    body={"name": filename, "parents": [subject_folder_id]},
                    media_body=media,
                    fields="id,name,size,webViewLink,mimeType",
                )
                .execute()
            )
        except Exception as exc:
            return await self._drive_google_error(user_id, exc, "file upload")

        doc = {
            "resource_id": new_id("res"),
            "user_id": user_id,
            "subject_id": subject_id,
            "resource_type": resource_type,
            "title": title or filename,
            "filename": filename,
            "mime_type": drive_file.get("mimeType", mime_type),
            "file_size": int(drive_file.get("size", len(contents))),
            "drive_file_id": drive_file["id"],
            "external_url": drive_file.get("webViewLink", ""),
            "source": "drive",
            "created_at": iso(now_utc()),
        }
        await self._res_repo.create(doc)
        return doc

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
                batch: List[Dict[str, Any]] = []
                files = GoogleDriveIntegration.list_children(service, sf["id"])
                for f in files:
                    if f["id"] in existing_ids:
                        skipped += 1
                        continue
                    batch.append({
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
                    })
                    existing_ids.add(f["id"])
                if batch:
                    await self._res_repo.create_many(batch)
                    synced += len(batch)

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

    async def view_resource(
        self, user_id: str, resource_id: str, backend_base: str
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        drive_file_id = res.get("drive_file_id")
        if not drive_file_id and res.get("external_url"):
            m = re.search(r"/file/d/([A-Za-z0-9_-]+)", res["external_url"])
            if not m:
                m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", res["external_url"])
            if m:
                drive_file_id = m.group(1)
        if drive_file_id:
            await self._drive._get_drive_creds(user_id, self._drive_repo)
            embed_url = f"{backend_base}/api/resources/{resource_id}/stream"
            return {
                "embed_url": embed_url,
                "view_url": res.get("external_url", ""),
                "kind": "drive",
            }
        return {
            "embed_url": res.get("external_url", ""),
            "view_url": res.get("external_url", ""),
            "kind": "external",
        }

    async def stream_resource(
        self, user_id: str, resource_id: str
    ) -> Dict[str, Any]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return {
                "error": "not_found",
                "message": "Resource not found",
                "status_code": 404,
            }
        drive_file_id = res.get("drive_file_id")
        if not drive_file_id:
            return {
                "error": "no_drive_file",
                "message": "Resource is not stored in Drive",
                "status_code": 400,
            }

        creds = await self._drive._get_drive_creds(user_id, self._drive_repo)
        if not creds:
            return {
                "error": "drive_not_connected",
                "message": "Drive not connected",
                "status_code": 400,
            }

        async def _download(token: str):
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{drive_file_id}?alt=media",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                return response.content

        try:
            content = await _download(creds.token)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                self._drive._creds_cache.pop(user_id, None)
                try:
                    creds = await self._drive._get_drive_creds(
                        user_id, self._drive_repo
                    )
                    if not creds:
                        return {
                            "error": "drive_access_denied",
                            "message": "Google Drive access expired — reconnect in Settings",
                            "status_code": 401,
                        }
                    content = await _download(creds.token)
                except Exception:
                    await self._drive_repo.delete(user_id)
                    return {
                        "error": "drive_access_denied",
                        "message": "Google Drive access expired — reconnect in Settings",
                        "status_code": 401,
                    }
            else:
                return {
                    "error": "drive_stream_failed",
                    "message": f"Google Drive returned {status}",
                    "status_code": 502,
                }
        except Exception:
            return {
                "error": "drive_stream_failed",
                "message": "Failed to fetch file from Google Drive",
                "status_code": 502,
            }

        return {
            "content": content,
            "mime_type": res.get("mime_type", "application/octet-stream"),
            "filename": res.get("filename", "file"),
        }

    async def toggle_page(
        self, user_id: str, resource_id: str, page: int, label: str = ""
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        existing = await self._note_repo.find(resource_id, user_id) or {}
        current = {
            p["page"]: p["label"]
            for p in normalize_pages(existing.get("important_pages"))
        }
        if page in current:
            current.pop(page, None)
            action = "removed"
        else:
            current[page] = (label or "")[:200]
            action = "added"
        new_pages = [
            {"page": p, "label": current[p]} for p in sorted(current.keys())
        ]
        await self._note_repo.upsert(
            resource_id,
            user_id,
            {"important_pages": new_pages, "content": existing.get("content", "")},
        )
        return {"important_pages": new_pages, "action": action, "page": page}

    async def set_page_label(
        self, user_id: str, resource_id: str, page: int, label: str
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        existing = await self._note_repo.find(resource_id, user_id) or {}
        current = {
            p["page"]: p["label"]
            for p in normalize_pages(existing.get("important_pages"))
        }
        if page not in current:
            return {"error": "not_flagged"}
        current[page] = (label or "")[:200]
        new_pages = [
            {"page": p, "label": current[p]} for p in sorted(current.keys())
        ]
        await self._note_repo.upsert(
            resource_id,
            user_id,
            {"important_pages": new_pages},
        )
        return {
            "important_pages": new_pages,
            "page": page,
            "label": current[page],
        }
