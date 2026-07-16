from __future__ import annotations

import os
import tempfile
import urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.api.providers import (
    get_staging_service,
)
from app.api.responses import err, ok
from app.core.ids import new_id
from app.core.logging import logger
from app.core.time import iso, now_utc
from app.schemas.auth import CurrentUser
from app.schemas.common import (
    ApprovedOut,
    BulkApprovedOut,
    DeletedOut,
    DismissedOut,
    Envelope,
    JobCreatedOut,
)
from app.schemas.staging import ApproveSpecificRequest
from app.services.staging import StagingService

router = APIRouter()


async def run_mistral_ocr_background(
    job_id: str,
    file_path: str,
    subject_id: str,
    source: str,
    user_id: str,
    service: StagingService,
):
    try:
        import sys

        sys.path.append(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        )
        from scripts.mistral_ocr import MistralOCRPipeline

        pipeline = MistralOCRPipeline(
            file_path, subject_id, job_id=job_id, source=source, user_id=user_id,
        )
        await pipeline.process_pdf()
        await service.mark_import_completed(job_id)
    except Exception as e:
        import logging

        logging.error(f"Mistral OCR pipeline failed for job {job_id}: {e}")
        await service.mark_import_failed(job_id, str(e))
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


async def _validate_and_download_url(
    url: str, max_bytes: int = 50 * 1024 * 1024
) -> tuple:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed")
    try:
        import ipaddress
        import socket

        host = parsed.hostname or ""
        addr = ipaddress.ip_address(socket.getaddrinfo(host, 80)[0][4][0])
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise ValueError("URL points to a private or local network address")
    except ValueError as e:
        raise e
    except Exception:
        raise ValueError("Could not resolve URL host")

    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, timeout=30) as resp:
            ctype = (resp.headers.get("content-type", "") or "").lower()
            if not ctype.startswith("application/pdf"):
                raise ValueError(
                    f"URL returned Content-Type '{ctype}', expected application/pdf"
                )
            content = bytearray()
            async for chunk in resp.aiter_bytes():
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise ValueError(
                        f"Response exceeds {max_bytes // (1024*1024)}MB limit"
                    )

    result = bytes(content)
    if result[:4] != b"%PDF":
        raise ValueError("Downloaded content is not a valid PDF")
    return result, url.split("/")[-1] or "remote_file.pdf"


SUPPORTED_OCR_ENGINES = {"mistral"}


@router.post("/import/pdf", response_model=Envelope[JobCreatedOut])
async def import_pdf(
    background_tasks: BackgroundTasks,
    subject_id: str = Form(...),
    engine: str = Form("mistral"),
    source: str = Form(""),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    if not file and not url:
        return err("missing_input", "Must provide either a file or a URL", 400)
    if engine not in SUPPORTED_OCR_ENGINES:
        return err(
            "unsupported_engine",
            f"OCR engine '{engine}' is not supported",
            400,
        )

    job_id = new_id("job")

    try:
        if file:
            contents = await file.read()
            if not contents:
                return err("empty_file", "Empty file", 400)
            if len(contents) > 50 * 1024 * 1024:
                return err("too_large", "File exceeds 50MB limit", 413)
            ctype = (file.content_type or "").lower()
            if ctype and not ctype.startswith("application/pdf"):
                return err("invalid_type", "Only PDF files are accepted", 400)
            if contents[:4] != b"%PDF":
                return err("invalid_pdf", "File does not appear to be a valid PDF", 400)
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf", prefix=f"ocr_{job_id}_"
            )
            file_path = tmp.name
            tmp.write(contents)
            tmp.close()
            filename = (
                os.path.basename(file.filename or "file.pdf").replace("\x00", "")
                or "file.pdf"
            )
        elif url:
            contents, filename = await _validate_and_download_url(url)
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf", prefix=f"ocr_{job_id}_"
            )
            file_path = tmp.name
            tmp.write(contents)
            tmp.close()

        await service.create_import_job({
            "job_id": job_id,
            "user_id": user.user_id,
            "filename": filename,
            "engine": engine,
            "source": source,
            "status": "PROCESSING",
            "progress": 0,
            "total_pages": 0,
            "created_at": iso(now_utc()),
        })

    except Exception as e:
        logger.error("OCR import upload failed for job %s: %s", job_id, e, exc_info=True)
        return err("upload_failed", "Failed to process upload", 400)

    background_tasks.add_task(
        run_mistral_ocr_background,
        job_id,
        file_path,
        subject_id,
        source,
        user.user_id,
        service,
    )
    return ok({"job_id": job_id})


@router.get("/import/jobs", response_model=Envelope[list])
async def list_import_jobs(
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    return ok(await service.list_import_jobs(user.user_id))


@router.delete("/import/jobs/{job_id}", response_model=Envelope[DismissedOut])
async def dismiss_import_job(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    await service.dismiss_import_job(user.user_id, job_id)
    return ok({"dismissed": 1})


@router.get("/staging", response_model=Envelope[list])
async def list_staging_items(
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    return ok(await service.list_staging_items(user.user_id))


@router.delete("/staging/{staging_id}", response_model=Envelope[DeletedOut])
async def discard_staging_item(
    staging_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    if await service.discard_staging_item(user.user_id, staging_id) == 0:
        return err("not_found", "Staging item not found", 404)
    return ok({"deleted": 1})


@router.delete("/staging", response_model=Envelope[DeletedOut])
async def clear_all_staging(
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    return ok({"deleted": await service.clear_staging(user.user_id)})


@router.post("/staging/approve-specific", response_model=Envelope[ApprovedOut])
async def approve_specific_item(
    body: ApproveSpecificRequest,
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    result = await service.approve_specific(user.user_id, body.staging_id)
    if result is None:
        return err("not_found", "Staging item not found", 404)
    return ok(result)


@router.post("/staging/bulk-approve", response_model=Envelope[BulkApprovedOut])
async def bulk_approve_staging_items(
    user: CurrentUser = Depends(get_current_user),
    service: StagingService = Depends(get_staging_service),
):
    result = await service.bulk_approve(user.user_id)
    if result is None:
        return err("no_items", "No ready items to approve", 400)
    return ok(result)
