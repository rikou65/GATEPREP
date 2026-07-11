from __future__ import annotations

import io
import os
import re
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import RedirectResponse
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.core.config import Settings
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
from app.schemas.resources import PageLabelIn, ResourceIn, ResourceNotesIn, TogglePageIn
from app.services.resources import (
    ResourceService,
    normalize_pages,
)

router = APIRouter()


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
        return {
            "status": status,
            "reason": reason,
            "message": message,
        }
    return {"status": None, "reason": "", "message": str(exc)}


async def _drive_google_error(
    db,
    user_id: str,
    drive: GoogleDriveIntegration,
    exc: Exception,
    stage: str,
):
    details = _google_api_error(exc)
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
        await DriveCredentialRepository(db).delete(user_id)
        drive._creds_cache.pop(user_id, None)
        return err(
            "drive_reconnect_required",
            "Google Drive access needs to be reconnected in Settings.",
            401,
        )

    if status in (429, 500, 502, 503, 504) or reason in {
        "ratelimitexceeded",
        "userratelimitexceeded",
        "backenderror",
    }:
        return err(
            "drive_retry_later",
            "Google Drive is temporarily unavailable. Try the upload again.",
            503,
        )

    return err(
        "drive_google_api_failed",
        f"Google Drive folder setup failed: {message}",
        502,
    )


def _build(request: Request):
    db = request.app.state.db
    settings: Settings = request.app.state.settings
    res_repo = ResourceRepository(db)
    note_repo = ResourceNoteRepository(db)
    drive_repo = DriveCredentialRepository(db)
    subject_repo = SubjectRepository(db)
    drive = GoogleDriveIntegration(settings)
    svc = ResourceService(res_repo, note_repo, drive_repo, subject_repo, drive)
    return db, settings, res_repo, note_repo, drive_repo, subject_repo, drive, svc


@router.get("/drive/connect")
async def drive_connect(
    request: Request,
    user=Depends(get_current_user),
):
    db, settings, _, _, _, _, drive, svc = _build(request)
    if not settings.GOOGLE_DRIVE_CLIENT_ID:
        return err("config", "Google Drive not configured", 500)

    from app.repositories.oauth_states import OAuthStateRepository
    from app.services.auth.oauth_state_service import OAuthStateService

    oauth = OAuthStateService(OAuthStateRepository(db))
    state = await oauth.generate(user["user_id"], "drive")
    return ok({"authorization_url": drive.build_connect_url(state)})


@router.get("/drive/callback")
async def drive_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
):
    db = request.app.state.db
    settings: Settings = request.app.state.settings

    from app.repositories.oauth_states import OAuthStateRepository
    from app.services.auth.oauth_state_service import OAuthStateService

    oauth = OAuthStateService(OAuthStateRepository(db))
    user_id = await oauth.consume(state, "drive")
    frontend = settings.FRONTEND_URL or "http://localhost:3000"
    if not user_id:
        return RedirectResponse(url=f"{frontend}/settings?drive=error")

    _, _, _, _, _, _, drive, svc = _build(request)
    success = await svc.handle_drive_callback(user_id, code)
    if not success:
        return RedirectResponse(url=f"{frontend}/settings?drive=error")

    try:
        sync_result = await svc.sync_drive(user_id)
    except Exception:
        pass
    return RedirectResponse(url=f"{frontend}/settings?drive=connected")


@router.get("/drive/status")
async def drive_status(
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, drive_repo, _, _, _ = _build(request)
    doc = await drive_repo.find(user["user_id"])
    if not doc:
        return ok({"connected": False})
    return ok({
        "connected": True,
        "user_id": user["user_id"],
        "drive_email": doc.get("drive_email", ""),
        "connected_at": doc.get("connected_at"),
    })


@router.post("/drive/refresh")
async def drive_refresh(
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, drive_repo, _, drive, _ = _build(request)
    creds = await drive._get_drive_creds(user["user_id"], drive_repo)
    if not creds:
        return err("drive_not_connected", "Drive not connected", 400)
    return ok({"refreshed": True, "valid": creds.valid})


@router.post("/drive/sync")
async def drive_sync(
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, _, _, _, svc = _build(request)
    result = await svc.sync_drive(user["user_id"])
    if isinstance(result, dict) and "error" in result:
        return err("sync_failed", result["error"], 400)
    return ok(result)


@router.post("/drive/disconnect")
async def drive_disconnect(
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, drive_repo, _, drive, _ = _build(request)
    doc = await drive_repo.find(user["user_id"])
    if doc and doc.get("refresh_token"):
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": doc["refresh_token"]},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                )
        except Exception:
            pass
    await drive_repo.delete(user["user_id"])
    drive._creds_cache.pop(user["user_id"], None)
    return ok({"disconnected": True})


@router.post("/resources")
async def create_resource(
    body: ResourceIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, _, _, _, svc = _build(request)
    doc = await svc.create(
        user["user_id"],
        body.subject_id,
        body.resource_type,
        body.title,
        body.external_url or "",
        body.file_size or 0,
    )
    return ok(doc)


@router.get("/resources")
async def list_resources(
    request: Request,
    subject_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    user=Depends(get_current_user),
):
    _, _, _, _, _, _, _, svc = _build(request)
    docs = await svc.list(user["user_id"], subject_id, resource_type)
    return ok(docs)


@router.delete("/resources/{resource_id}")
async def delete_resource(
    resource_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, _, _, _, svc = _build(request)
    deleted = await svc.delete(user["user_id"], resource_id)
    return ok({"deleted": deleted})


@router.get("/resources/{resource_id}/notes")
async def get_resource_notes(
    resource_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, _, _, _, svc = _build(request)
    result = await svc.get_notes(resource_id, user["user_id"])
    if result is None:
        return err("not_found", "Resource not found", 404)
    return ok(result)


@router.post("/resources/{resource_id}/notes")
async def save_resource_notes(
    resource_id: str,
    body: ResourceNotesIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, _, _, _, svc = _build(request)
    result = await svc.save_notes(
        resource_id,
        user["user_id"],
        body.content,
        body.important_pages,
    )
    if result is None:
        return err("not_found", "Resource not found", 404)
    return ok(result)


@router.post("/resources/{resource_id}/pages/toggle")
async def toggle_important_page(
    resource_id: str,
    body: TogglePageIn,
    request: Request,
    user=Depends(get_current_user),
):
    if body.page <= 0:
        return err("bad_page", "page must be a positive integer", 400)
    _, _, res_repo, note_repo, _, _, _, _ = _build(request)
    res = await res_repo.find_by_id(resource_id, user["user_id"])
    if not res:
        return err("not_found", "Resource not found", 404)
    existing = await note_repo.find(resource_id, user["user_id"]) or {}
    current = {
        p["page"]: p["label"]
        for p in normalize_pages(existing.get("important_pages"))
    }
    if body.page in current:
        current.pop(body.page, None)
        action = "removed"
    else:
        current[body.page] = (body.label or "")[:200]
        action = "added"
    new_pages = [
        {"page": p, "label": current[p]} for p in sorted(current.keys())
    ]
    await note_repo.upsert(
        resource_id,
        user["user_id"],
        {"important_pages": new_pages, "content": existing.get("content", "")},
    )
    return ok({"important_pages": new_pages, "action": action, "page": body.page})


@router.post("/resources/{resource_id}/pages/label")
async def set_page_label(
    resource_id: str,
    body: PageLabelIn,
    request: Request,
    user=Depends(get_current_user),
):
    if body.page <= 0:
        return err("bad_page", "page must be a positive integer", 400)
    _, _, res_repo, note_repo, _, _, _, _ = _build(request)
    res = await res_repo.find_by_id(resource_id, user["user_id"])
    if not res:
        return err("not_found", "Resource not found", 404)
    existing = await note_repo.find(resource_id, user["user_id"]) or {}
    current = {
        p["page"]: p["label"]
        for p in normalize_pages(existing.get("important_pages"))
    }
    if body.page not in current:
        return err("not_flagged", "Page is not flagged as important", 400)
    current[body.page] = (body.label or "")[:200]
    new_pages = [
        {"page": p, "label": current[p]} for p in sorted(current.keys())
    ]
    await note_repo.upsert(
        resource_id,
        user["user_id"],
        {"important_pages": new_pages},
    )
    return ok({
        "important_pages": new_pages,
        "page": body.page,
        "label": current[body.page],
    })


@router.post("/resources/upload")
async def resources_upload(
    request: Request,
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    resource_type: str = Form(...),
    title: Optional[str] = Form(None),
    user=Depends(get_current_user),
):
    db, settings, res_repo, _, drive_repo, subject_repo, drive, _ = _build(request)
    try:
        service = await drive.build_service(user["user_id"], drive_repo)
    except Exception as exc:
        logger.warning(
            "Drive upload failed while building Drive service for %s: %s",
            user["user_id"],
            exc,
            exc_info=True,
        )
        return err(
            "drive_service_failed",
            "Could not prepare Google Drive access. Reconnect Drive in Settings.",
            502,
        )
    if not service:
        logger.info(
            "Drive upload blocked because Drive is not connected for %s",
            user["user_id"],
        )
        return err("drive_not_connected", "Connect Google Drive first", 400)

    subj = await subject_repo.find_by_id(subject_id)
    if not subj:
        logger.info(
            "Drive upload failed because subject was not found: user=%s subject=%s",
            user["user_id"],
            subject_id,
        )
        return err("not_found", "Subject not found", 404)

    contents = await file.read()
    if not contents:
        return err("empty_file", "Empty file", 400)
    if len(contents) > 200 * 1024 * 1024:
        return err("too_large", "File exceeds 200MB", 413)

    ALLOWED_EXTENSIONS = {
        ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp",
        ".doc", ".docx", ".txt", ".csv", ".xls", ".xlsx", ".ppt", ".pptx",
    }
    ALLOWED_MIMES = {
        "application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain", "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    ext = (os.path.splitext((file.filename or "").strip())[1] or "").lower()
    if ext not in ALLOWED_EXTENSIONS:
        return err("invalid_extension", f"File extension '{ext}' not allowed", 400)
    declared_mime = (file.content_type or "").lower()
    if declared_mime not in ALLOWED_MIMES:
        return err("invalid_mime", f"Content type '{declared_mime}' not allowed", 400)
    if ext == ".pdf" and contents[:4] != b"%PDF":
        return err("invalid_pdf", "File does not appear to be a valid PDF", 400)

    filename = (os.path.basename(file.filename or "file")).replace("\x00", "") or "file"
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
        return await _drive_google_error(
            db, user["user_id"], drive, exc, "folder setup"
        )

    media = MediaIoBaseUpload(
        io.BytesIO(contents), mimetype=declared_mime, resumable=False
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
        return await _drive_google_error(
            db, user["user_id"], drive, exc, "file upload"
        )

    doc = {
        "resource_id": new_id("res"),
        "user_id": user["user_id"],
        "subject_id": subject_id,
        "resource_type": resource_type,
        "title": title or filename,
        "filename": filename,
        "mime_type": drive_file.get("mimeType", declared_mime),
        "file_size": int(drive_file.get("size", len(contents))),
        "drive_file_id": drive_file["id"],
        "external_url": drive_file.get("webViewLink", ""),
        "source": "drive",
        "created_at": iso(now_utc()),
    }
    await res_repo.create(doc)
    return ok(doc)


@router.get("/resources/{resource_id}/view")
async def resource_view(
    resource_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, res_repo, _, drive_repo, _, drive, _ = _build(request)
    res = await res_repo.find_by_id(resource_id, user["user_id"])
    if not res:
        return err("not_found", "Resource not found", 404)
    drive_file_id = res.get("drive_file_id")
    if not drive_file_id and res.get("external_url"):
        m = re.search(r"/file/d/([A-Za-z0-9_-]+)", res["external_url"])
        if not m:
            m = re.search(r"[?&]id=([A-Za-z0-9_-]+)", res["external_url"])
        if m:
            drive_file_id = m.group(1)
    if drive_file_id:
        await drive._get_drive_creds(user["user_id"], drive_repo)
        backend_base = str(request.base_url).rstrip("/")
        embed_url = f"{backend_base}/api/resources/{resource_id}/stream"
        return ok({
            "embed_url": embed_url,
            "view_url": res.get("external_url", ""),
            "kind": "drive",
        })
    return ok({
        "embed_url": res.get("external_url", ""),
        "view_url": res.get("external_url", ""),
        "kind": "external",
    })


@router.get("/resources/{resource_id}/stream")
async def resource_stream(
    resource_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, res_repo, _, drive_repo, _, drive, _ = _build(request)
    res = await res_repo.find_by_id(resource_id, user["user_id"])
    if not res:
        return err("not_found", "Resource not found", 404)
    drive_file_id = res.get("drive_file_id")
    if not drive_file_id:
        return err("no_drive_file", "Resource is not stored in Drive", 400)

    creds = await drive._get_drive_creds(user["user_id"], drive_repo)
    if not creds:
        return err("drive_not_connected", "Drive not connected", 400)

    mime_type = res.get("mime_type", "application/octet-stream")
    filename = res.get("filename", "file")

    async def _download(token: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{drive_file_id}?alt=media",
                headers={"Authorization": f"Bearer {token}"},
                timeout=None,
            )
            r.raise_for_status()
            return r.content

    try:
        content = await _download(creds.token)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (401, 403):
            drive._creds_cache.pop(user["user_id"], None)
            try:
                creds = await drive._get_drive_creds(user["user_id"], drive_repo)
                if not creds:
                    return err(
                        "drive_access_denied",
                        "Google Drive access expired — reconnect in Settings",
                        401,
                    )
                content = await _download(creds.token)
            except Exception:
                await drive_repo.delete(user["user_id"])
                return err(
                    "drive_access_denied",
                    "Google Drive access expired — reconnect in Settings",
                    401,
                )
        else:
            return err("drive_stream_failed", f"Google Drive returned {status}", 502)
    except Exception as e:
        return err("drive_stream_failed", "Failed to fetch file from Google Drive", 502)

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(content)),
            "Cache-Control": "private, max-age=300",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )
