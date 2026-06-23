from __future__ import annotations

import io
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from shared import (
    DRIVE_ROOT_NAME,
    DRIVE_SCOPES,
    RESOURCE_TYPE_FOLDERS,
    async_post,
    db,
    err,
    get_current_user,
    iso,
    logger,
    new_id,
    now_utc,
    ok,
    settings,
)

router = APIRouter()


def _drive_client_config() -> Dict[str, Any]:
    return {
        "web": {
            "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_DRIVE_REDIRECT_URI],
        }
    }




async def _get_drive_creds(user_id: str):
    doc = await db.drive_credentials.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        return None
    expiry = None
    if doc.get("expiry"):
        try:
            expiry = datetime.fromisoformat(doc["expiry"])
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
        except Exception:
            expiry = None
    creds = Credentials(
        token=doc.get("access_token"),
        refresh_token=doc.get("refresh_token"),
        token_uri=doc.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=settings.GOOGLE_DRIVE_CLIENT_ID,
        client_secret=settings.GOOGLE_DRIVE_CLIENT_SECRET,
        scopes=doc.get("scopes") or DRIVE_SCOPES,
        expiry=expiry.replace(tzinfo=None) if expiry else None,
    )

    if not creds.valid and creds.refresh_token:
        creds.refresh(GoogleRequest())
        new_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
        await db.drive_credentials.update_one(
            {"user_id": user_id},
            {"$set": {
                "access_token": creds.token,
                "expiry": iso(new_expiry) if new_expiry else None,
                "updated_at": iso(now_utc()),
            }},
        )
    return creds


async def _build_drive_service(user_id: str):
    creds = await _get_drive_creds(user_id)
    if not creds:
        return None
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_folder(service, name: str, parent_id: Optional[str]) -> Optional[str]:
    q_parts = [
        f"name='{name.replace(chr(39), chr(92)+chr(39))}'",
        "mimeType='application/vnd.google-apps.folder'",
        "trashed=false",
    ]
    if parent_id:
        q_parts.append(f"'{parent_id}' in parents")
    res = service.files().list(
        q=" and ".join(q_parts), fields="files(id,name)", pageSize=10,
        spaces="drive",
    ).execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def _get_or_create_folder(service, name: str, parent_id: Optional[str] = None) -> str:
    fid = _find_folder(service, name, parent_id)
    if fid:
        return fid
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    created = service.files().create(body=meta, fields="id").execute()
    return created["id"]


def _ensure_resource_folder(service, resource_type: str, subject_name: str) -> str:
    root_id = _get_or_create_folder(service, DRIVE_ROOT_NAME, None)
    type_id = _get_or_create_folder(service, resource_type, root_id)
    subject_id = _get_or_create_folder(service, subject_name, type_id)
    return subject_id


def _list_children(service, parent_id: str, mime_type: Optional[str] = None) -> List[Dict[str, Any]]:
    q_parts = [f"'{parent_id}' in parents", "trashed=false"]
    if mime_type:
        q_parts.append(f"mimeType='{mime_type}'")
    else:
        q_parts.append("mimeType!='application/vnd.google-apps.folder'")
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


async def _sync_drive_to_resources(user_id: str) -> Dict[str, Any]:
    service = await _build_drive_service(user_id)
    if not service:
        return {"synced": 0, "skipped": 0, "error": "drive_not_connected"}

    subj_docs = await db.subjects.find({}, {"_id": 0, "subject_id": 1, "name": 1}).to_list(100)
    subj_by_name = {s["name"].lower(): s["subject_id"] for s in subj_docs}

    existing = await db.resources.find(
        {"user_id": user_id, "drive_file_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "drive_file_id": 1},
    ).to_list(10000)
    existing_ids = {r["drive_file_id"] for r in existing if r.get("drive_file_id")}

    folder_mime = "application/vnd.google-apps.folder"
    root_id = _find_folder(service, DRIVE_ROOT_NAME, None)
    if not root_id:
        return {"synced": 0, "skipped": 0, "error": "no_gateprep_folder"}

    synced = 0
    skipped = 0
    unknown_subjects: List[str] = []

    type_folders = _list_children(service, root_id, mime_type=folder_mime)
    for type_folder in type_folders:
        resource_type = type_folder["name"]
        subject_folders = _list_children(service, type_folder["id"], mime_type=folder_mime)
        for subj_folder in subject_folders:
            subj_name = subj_folder["name"]
            subject_id = subj_by_name.get(subj_name.lower())
            if not subject_id:
                if subj_name not in unknown_subjects:
                    unknown_subjects.append(subj_name)
                continue
            files = _list_children(service, subj_folder["id"])
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
                await db.resources.insert_one(dict(doc))
                existing_ids.add(f["id"])
                synced += 1

    return {"synced": synced, "skipped": skipped, "unknown_subjects": unknown_subjects}


@router.get("/drive/connect")
async def drive_connect(user=Depends(get_current_user)):
    if not settings.GOOGLE_DRIVE_CLIENT_ID:
        return err("config", "Google Drive not configured", 500)
    
    # Use manual URL construction to avoid automatic PKCE verifier issues
    params = {
        "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(DRIVE_SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": user["user_id"],
    }
    encoded_params = "&".join([f"{k}={urllib.parse.quote(v)}" for k, v in params.items()])
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{encoded_params}"
    return ok({"authorization_url": auth_url})


@router.get("/drive/callback")
async def drive_callback(code: str = Query(...), state: str = Query(...)):
    try:
        # 1. Exchange code for tokens manually
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_DRIVE_REDIRECT_URI,
                },
                timeout=15
            )
            if token_resp.status_code != 200:
                logger.error(f"Drive token exchange failed: {token_resp.text}")
                frontend = settings.FRONTEND_URL or "http://localhost:3000"
                return RedirectResponse(url=f"{frontend}/settings?drive=error")
            
            tokens = token_resp.json()
            
            # 2. Get Drive user email
            about_resp = await client.get(
                "https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                timeout=10
            )
            drive_email = ""
            if about_resp.status_code == 200:
                drive_email = about_resp.json().get("user", {}).get("emailAddress", "")

        # 3. Save to database
        # Convert expiry if present
        expiry_iso = None
        if "expires_in" in tokens:
            expiry_dt = now_utc() + timedelta(seconds=tokens["expires_in"])
            expiry_iso = iso(expiry_dt)

        set_data = {
            "user_id": state,
            "access_token": tokens.get("access_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": tokens.get("scope", "").split(" "),
            "expiry": expiry_iso,
            "drive_email": drive_email,
            "updated_at": iso(now_utc()),
        }
        if tokens.get("refresh_token"):
            set_data["refresh_token"] = tokens["refresh_token"]

        await db.drive_credentials.update_one(
            {"user_id": state},
            {"$set": set_data, "$setOnInsert": {"connected_at": iso(now_utc())}},
            upsert=True,
        )
        
        # 4. Trigger auto-sync
        try:
            sync_result = await _sync_drive_to_resources(state)
            logger.info(f"Drive auto-sync after connect for {state}: {sync_result}")
        except Exception as se:
            logger.warning(f"Drive auto-sync failed (non-fatal) for {state}: {se}")
        
        frontend = settings.FRONTEND_URL or "http://localhost:3000"
        return RedirectResponse(url=f"{frontend}/settings?drive=connected")
    except Exception as e:
        logger.error(f"Drive callback error: {e}")
        frontend = settings.FRONTEND_URL or "http://localhost:3000"
        return RedirectResponse(url=f"{frontend}/settings?drive=error")


@router.get("/drive/status")
async def drive_status(user=Depends(get_current_user)):
    doc = await db.drive_credentials.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        return ok({"connected": False})
    return ok({
        "connected": True,
        "drive_email": doc.get("drive_email", ""),
        "connected_at": doc.get("connected_at"),
    })


@router.post("/drive/sync")
async def drive_sync(user=Depends(get_current_user)):
    try:
        result = await _sync_drive_to_resources(user["user_id"])
        return ok(result)
    except Exception as e:
        logger.error(f"drive sync failed: {e}")
        return err("sync_failed", str(e), 500)


@router.post("/drive/disconnect")
async def drive_disconnect(user=Depends(get_current_user)):
    doc = await db.drive_credentials.find_one({"user_id": user["user_id"]}, {"_id": 0})
    if doc and doc.get("refresh_token"):
        try:
            await async_post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": doc["refresh_token"]},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Drive token revoke failed: {e}")
    await db.drive_credentials.delete_one({"user_id": user["user_id"]})
    return ok({"disconnected": True})


class ResourceIn(BaseModel):
    subject_id: str
    resource_type: str
    title: str
    external_url: Optional[str] = ""
    file_size: Optional[int] = 0


@router.post("/resources")
async def create_resource(body: ResourceIn, user=Depends(get_current_user)):
    doc = {
        "resource_id": new_id("res"), "user_id": user["user_id"],
        "subject_id": body.subject_id, "resource_type": body.resource_type,
        "title": body.title, "external_url": body.external_url or "",
        "file_size": body.file_size or 0, "created_at": iso(now_utc()),
        "source": "external",
    }
    await db.resources.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)


@router.get("/resources")
async def list_resources(subject_id: Optional[str] = None, resource_type: Optional[str] = None,
                        user=Depends(get_current_user)):
    q: Dict[str, Any] = {"user_id": user["user_id"]}
    if subject_id:
        q["subject_id"] = subject_id
    if resource_type:
        q["resource_type"] = resource_type
    docs = await db.resources.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return ok(docs)


@router.delete("/resources/{resource_id}")
async def delete_resource(resource_id: str, user=Depends(get_current_user)):
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0})
    if res and res.get("drive_file_id"):
        try:
            service = await _build_drive_service(user["user_id"])
            if service:
                service.files().delete(fileId=res["drive_file_id"]).execute()
        except Exception as e:
            logger.warning(f"Drive delete failed for {resource_id}: {e}")
    r = await db.resources.delete_one({"resource_id": resource_id, "user_id": user["user_id"]})
    await db.resource_notes.delete_one({"resource_id": resource_id, "user_id": user["user_id"]})
    return ok({"deleted": r.deleted_count})


def _normalize_pages(raw) -> List[Dict[str, Any]]:
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


def _resource_notes_view(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not doc:
        return {"content": "", "important_pages": []}
    return {
        "content": doc.get("content", "") or "",
        "important_pages": _normalize_pages(doc.get("important_pages")),
        "updated_at": doc.get("updated_at"),
    }


class ResourceNotesIn(BaseModel):
    content: Optional[str] = None
    important_pages: Optional[List[Any]] = None


class TogglePageIn(BaseModel):
    page: int
    label: Optional[str] = ""


class PageLabelIn(BaseModel):
    page: int
    label: str = ""


@router.get("/resources/{resource_id}/notes")
async def get_resource_notes(resource_id: str, user=Depends(get_current_user)):
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0, "resource_id": 1})
    if not res:
        return err("not_found", "Resource not found", 404)
    doc = await db.resource_notes.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0})
    return ok(_resource_notes_view(doc))


@router.post("/resources/{resource_id}/notes")
async def save_resource_notes(resource_id: str, body: ResourceNotesIn, user=Depends(get_current_user)):
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0, "resource_id": 1})
    if not res:
        return err("not_found", "Resource not found", 404)
    set_doc: Dict[str, Any] = {"updated_at": iso(now_utc())}
    if body.content is not None:
        set_doc["content"] = body.content
    if body.important_pages is not None:
        set_doc["important_pages"] = _normalize_pages(body.important_pages)
    await db.resource_notes.update_one(
        {"resource_id": resource_id, "user_id": user["user_id"]},
        {"$set": set_doc,
         "$setOnInsert": {
            "resource_id": resource_id, "user_id": user["user_id"],
            "created_at": iso(now_utc()),
         }},
        upsert=True,
    )
    doc = await db.resource_notes.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0})
    return ok(_resource_notes_view(doc))


@router.post("/resources/{resource_id}/pages/toggle")
async def toggle_important_page(resource_id: str, body: TogglePageIn, user=Depends(get_current_user)):
    if body.page <= 0:
        return err("bad_page", "page must be a positive integer", 400)
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0, "resource_id": 1})
    if not res:
        return err("not_found", "Resource not found", 404)
    existing = await db.resource_notes.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0, "important_pages": 1}) or {}
    current = {p["page"]: p["label"] for p in _normalize_pages(existing.get("important_pages"))}
    if body.page in current:
        current.pop(body.page, None)
        action = "removed"
    else:
        current[body.page] = (body.label or "")[:200]
        action = "added"
    new_pages = [{"page": p, "label": current[p]} for p in sorted(current.keys())]
    await db.resource_notes.update_one(
        {"resource_id": resource_id, "user_id": user["user_id"]},
        {"$set": {"important_pages": new_pages, "updated_at": iso(now_utc())},
         "$setOnInsert": {
            "resource_id": resource_id, "user_id": user["user_id"],
            "content": "", "created_at": iso(now_utc()),
         }},
        upsert=True,
    )
    return ok({"important_pages": new_pages, "action": action, "page": body.page})


@router.post("/resources/{resource_id}/pages/label")
async def set_page_label(resource_id: str, body: PageLabelIn, user=Depends(get_current_user)):
    if body.page <= 0:
        return err("bad_page", "page must be a positive integer", 400)
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0, "resource_id": 1})
    if not res:
        return err("not_found", "Resource not found", 404)
    existing = await db.resource_notes.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0, "important_pages": 1}) or {}
    current = {p["page"]: p["label"] for p in _normalize_pages(existing.get("important_pages"))}
    if body.page not in current:
        return err("not_flagged", "Page is not flagged as important", 400)
    current[body.page] = (body.label or "")[:200]
    new_pages = [{"page": p, "label": current[p]} for p in sorted(current.keys())]
    await db.resource_notes.update_one(
        {"resource_id": resource_id, "user_id": user["user_id"]},
        {"$set": {"important_pages": new_pages, "updated_at": iso(now_utc())}},
    )
    return ok({"important_pages": new_pages, "page": body.page, "label": current[body.page]})


@router.post("/resources/upload")
async def resources_upload(
    file: UploadFile = File(...),
    subject_id: str = Form(...),
    resource_type: str = Form(...),
    title: Optional[str] = Form(None),
    user=Depends(get_current_user),
):
    subject = await db.subjects.find_one({"subject_id": subject_id}, {"_id": 0})
    if not subject:
        return err("not_found", "Subject not found", 404)
    service = await _build_drive_service(user["user_id"])
    if not service:
        return err("drive_not_connected", "Connect Google Drive first", 400)
    contents = await file.read()
    if not contents:
        return err("empty_file", "Empty file", 400)
    if len(contents) > 100 * 1024 * 1024:
        return err("too_large", "File exceeds 100MB", 413)
    parent_id = _ensure_resource_folder(service, resource_type, subject["name"])
    media = MediaIoBaseUpload(io.BytesIO(contents), mimetype=file.content_type or "application/octet-stream", resumable=False)
    drive_file = service.files().create(
        body={"name": file.filename, "parents": [parent_id]},
        media_body=media,
        fields="id,name,size,webViewLink,mimeType",
    ).execute()
    doc = {
        "resource_id": new_id("res"),
        "user_id": user["user_id"],
        "subject_id": subject_id,
        "resource_type": resource_type,
        "title": title or file.filename,
        "filename": file.filename,
        "mime_type": drive_file.get("mimeType", file.content_type or ""),
        "file_size": int(drive_file.get("size", len(contents))),
        "drive_file_id": drive_file["id"],
        "external_url": drive_file.get("webViewLink", ""),
        "source": "drive",
        "created_at": iso(now_utc()),
    }
    await db.resources.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)


@router.get("/resources/{resource_id}/view")
async def resource_view(resource_id: str, request: Request, user=Depends(get_current_user)):
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0})
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
        backend_base = str(request.base_url).rstrip("/")
        embed_url = f"{backend_base}/api/resources/{resource_id}/stream"
        web_view = res.get("external_url", "")
        if res.get("drive_file_id"):
            service = await _build_drive_service(user["user_id"])
            if service:
                try:
                    meta = service.files().get(fileId=drive_file_id, fields="webViewLink,webContentLink,mimeType").execute()
                    web_view = meta.get("webViewLink") or web_view
                except Exception as e:
                    logger.warning(f"Drive view fetch failed: {e}")
        return ok({"embed_url": embed_url, "view_url": web_view, "kind": "drive"})
    return ok({"embed_url": res.get("external_url", ""), "view_url": res.get("external_url", ""), "kind": "external"})


@router.get("/resources/{resource_id}/stream")
async def resource_stream(resource_id: str, user=Depends(get_current_user)):
    res = await db.resources.find_one({"resource_id": resource_id, "user_id": user["user_id"]}, {"_id": 0})
    if not res:
        return err("not_found", "Resource not found", 404)
    drive_file_id = res.get("drive_file_id")
    if not drive_file_id:
        return err("no_drive_file", "Resource is not stored in Drive", 400)
    
    creds = await _get_drive_creds(user["user_id"])
    if not creds:
        return err("drive_not_connected", "Drive not connected", 400)
        
    try:
        # Get metadata for headers
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        meta = service.files().get(fileId=drive_file_id, fields="mimeType,name,size").execute()
        
        async def stream_file():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"https://www.googleapis.com/drive/v3/files/{drive_file_id}?alt=media",
                    headers={"Authorization": f"Bearer {creds.token}"},
                    timeout=None
                ) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            stream_file(),
            media_type=meta.get("mimeType", "application/octet-stream"),
            headers={
                "Content-Disposition": f'inline; filename="{meta.get("name", "file")}"',
                "Content-Length": str(meta.get("size", "")),
                "Cache-Control": "private, max-age=300",
                "X-Frame-Options": "SAMEORIGIN",
            },
        )
    except Exception as e:
        logger.error(f"Drive stream failed for {resource_id}: {e}")
        return err("stream_failed", str(e), 502)
