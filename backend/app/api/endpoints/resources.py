from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user
from app.api.providers import (
    get_resource_service,
    get_settings,
)
from app.api.responses import err, ok
from app.core.config import Settings
from app.schemas.auth import CurrentUser
from app.schemas.common import (
    DeletedOut,
    DisconnectedOut,
    DriveStatusOut,
    Envelope,
    GoogleUrlOut,
    LabelPageOut,
    RefreshedOut,
    ResourceViewOut,
    SyncedOut,
    TogglePageOut,
)
from app.schemas.resources import PageLabelIn, ResourceIn, ResourceNotesIn, TogglePageIn
from app.services.resources import ResourceService

router = APIRouter()


@router.get("/drive/connect", response_model=Envelope[GoogleUrlOut])
async def drive_connect(
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    authorization_url = await svc.build_drive_connect_url(user.user_id)
    if not authorization_url:
        return err("config", "Google Drive not configured", 500)
    return ok({"authorization_url": authorization_url})


@router.get("/drive/callback")
async def drive_callback(
    code: str = Query(...),
    state: str = Query(...),
    settings: Settings = Depends(get_settings),
    svc: ResourceService = Depends(get_resource_service),
):
    frontend = settings.FRONTEND_URL or "http://localhost:3000"
    success = await svc.handle_drive_oauth_callback(state, code)
    if not success:
        return RedirectResponse(url=f"{frontend}/settings?drive=error")
    return RedirectResponse(url=f"{frontend}/settings?drive=connected")


@router.get("/drive/status", response_model=Envelope[DriveStatusOut])
async def drive_status(
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    return ok(await svc.get_drive_status(user.user_id))


@router.post("/drive/refresh", response_model=Envelope[RefreshedOut])
async def drive_refresh(
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    result = await svc.refresh_drive(user.user_id)
    if result is None:
        return err("drive_not_connected", "Drive not connected", 400)
    return ok(result)


@router.post("/drive/sync", response_model=Envelope[SyncedOut])
async def drive_sync(
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    result = await svc.sync_drive(user.user_id)
    if isinstance(result, dict) and "error" in result:
        return err("sync_failed", result["error"], 400)
    return ok(result)


@router.post("/drive/disconnect", response_model=Envelope[DisconnectedOut])
async def drive_disconnect(
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    await svc.disconnect_drive(user.user_id)
    return ok({"disconnected": True})


@router.post("/resources", response_model=Envelope[dict])
async def create_resource(
    body: ResourceIn,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    doc = await svc.create(
        user.user_id,
        body.subject_id,
        body.resource_type,
        body.title,
        body.external_url or "",
        body.file_size or 0,
    )
    return ok(doc)


@router.get("/resources", response_model=Envelope[List[dict]])
async def list_resources(
    subject_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    docs = await svc.list(user.user_id, subject_id, resource_type)
    return ok(docs)


@router.delete("/resources/{resource_id}", response_model=Envelope[DeletedOut])
async def delete_resource(
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    deleted = await svc.delete(user.user_id, resource_id)
    return ok({"deleted": deleted})


@router.get("/resources/{resource_id}/notes", response_model=Envelope[dict])
async def get_resource_notes(
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    result = await svc.get_notes(resource_id, user.user_id)
    if result is None:
        return err("not_found", "Resource not found", 404)
    return ok(result)


@router.post("/resources/{resource_id}/notes", response_model=Envelope[dict])
async def save_resource_notes(
    resource_id: str,
    body: ResourceNotesIn,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    result = await svc.save_notes(
        resource_id,
        user.user_id,
        body.content,
        body.important_pages,
    )
    if result is None:
        return err("not_found", "Resource not found", 404)
    return ok(result)


@router.post("/resources/{resource_id}/pages/toggle", response_model=Envelope[TogglePageOut])
async def toggle_important_page(
    resource_id: str,
    body: TogglePageIn,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    if body.page <= 0:
        return err("bad_page", "page must be a positive integer", 400)
    result = await svc.toggle_page(user.user_id, resource_id, body.page, body.label or "")
    if result is None:
        return err("not_found", "Resource not found", 404)
    return ok(result)


@router.post("/resources/{resource_id}/pages/label", response_model=Envelope[LabelPageOut])
async def set_page_label(
    resource_id: str,
    body: PageLabelIn,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    if body.page <= 0:
        return err("bad_page", "page must be a positive integer", 400)
    result = await svc.set_page_label(user.user_id, resource_id, body.page, body.label)
    if result is None:
        return err("not_found", "Resource not found", 404)
    if isinstance(result, dict) and "error" in result:
        return err("not_flagged", "Page is not flagged as important", 400)
    return ok(result)


@router.post("/resources/upload", response_model=Envelope[dict])
async def resources_upload(
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    resource_type: str = Form(...),
    title: Optional[str] = Form(None),
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    contents = await file.read()
    result = await svc.upload_from_computer(
        user.user_id,
        subject_id,
        resource_type,
        title,
        file.filename,
        file.content_type,
        contents,
    )
    if isinstance(result, dict) and "error" in result:
        return err(
            result["error"],
            result.get("message", "Upload failed"),
            result.get("status_code", 400),
        )
    return ok(result)


@router.get("/resources/{resource_id}/view", response_model=Envelope[ResourceViewOut])
async def resource_view(
    resource_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    result = await svc.view_resource(
        user.user_id, resource_id, str(request.base_url).rstrip("/")
    )
    if result is None:
        return err("not_found", "Resource not found", 404)
    return ok(result)


@router.get("/resources/{resource_id}/stream")
async def resource_stream(
    resource_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: ResourceService = Depends(get_resource_service),
):
    result = await svc.stream_resource(user.user_id, resource_id)
    if "error" in result:
        return err(
            result["error"],
            result.get("message", "Failed to stream resource"),
            result.get("status_code", 400),
        )

    return Response(
        content=result["content"],
        media_type=result["mime_type"],
        headers={
            "Content-Disposition": f'inline; filename="{result["filename"]}"',
            "Content-Length": str(len(result["content"])),
            "Cache-Control": "private, max-age=300",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )
