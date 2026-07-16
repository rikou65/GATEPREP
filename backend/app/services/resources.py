from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.integrations.google_drive import GoogleDriveIntegration
from app.repositories.resources import (
    DriveCredentialRepository,
    ResourceNoteRepository,
    ResourceRepository,
)
from app.repositories.subjects import SubjectRepository
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.resource_drive import ResourceDriveService
from app.services.resource_notes import ResourceNotesService


class ResourceService:
    """Facade for resource operations used by the API layer.

    CRUD, Drive, and notes/bookmark responsibilities live in smaller services so
    endpoints keep one dependency without this class becoming a dumping ground.
    """

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
        self._drive = drive_integration
        self._drive_repo = drive_repo
        self._notes = ResourceNotesService(res_repo, note_repo)
        self._drive_resources = ResourceDriveService(
            res_repo,
            drive_repo,
            subject_repo,
            drive_integration,
            oauth_state_service,
        )

    async def create(
        self,
        user_id: str,
        subject_id: str,
        resource_type: str,
        title: str,
        external_url: str,
        file_size: int,
    ) -> Dict[str, Any]:
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

    async def list(
        self,
        user_id: str,
        subject_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> list:
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

    async def build_drive_connect_url(self, user_id: str) -> Optional[str]:
        return await self._drive_resources.build_connect_url(user_id)

    async def handle_drive_oauth_callback(self, state: str, code: str) -> bool:
        return await self._drive_resources.handle_oauth_callback(state, code)

    async def get_drive_status(self, user_id: str) -> Dict[str, Any]:
        return await self._drive_resources.get_status(user_id)

    async def refresh_drive(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._drive_resources.refresh(user_id)

    async def disconnect_drive(self, user_id: str) -> None:
        await self._drive_resources.disconnect(user_id)

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
        return await self._drive_resources.upload_from_computer(
            user_id,
            subject_id,
            resource_type,
            title,
            original_filename,
            declared_mime,
            contents,
        )

    async def sync_drive(self, user_id: str) -> Dict[str, Any]:
        return await self._drive_resources.sync(user_id)

    async def handle_drive_callback(self, user_id: str, code: str) -> bool:
        return await self._drive_resources.handle_callback(user_id, code)

    async def view_resource(
        self, user_id: str, resource_id: str, backend_base: str
    ) -> Optional[Dict[str, Any]]:
        return await self._drive_resources.view_resource(
            user_id, resource_id, backend_base
        )

    async def stream_resource(
        self, user_id: str, resource_id: str
    ) -> Dict[str, Any]:
        return await self._drive_resources.stream_resource(user_id, resource_id)

    async def get_notes(
        self, resource_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        return await self._notes.get_notes(resource_id, user_id)

    async def save_notes(
        self,
        resource_id: str,
        user_id: str,
        content: Optional[str],
        important_pages: Optional[list],
    ) -> Optional[Dict[str, Any]]:
        return await self._notes.save_notes(
            resource_id, user_id, content, important_pages
        )

    async def toggle_page(
        self, user_id: str, resource_id: str, page: int, label: str = ""
    ) -> Optional[Dict[str, Any]]:
        return await self._notes.toggle_page(user_id, resource_id, page, label)

    async def set_page_label(
        self, user_id: str, resource_id: str, page: int, label: str
    ) -> Optional[Dict[str, Any]]:
        return await self._notes.set_page_label(user_id, resource_id, page, label)
