from __future__ import annotations

import os
import tempfile
import urllib.parse
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.repositories.staging import (
    ImportedQuestionRepository,
    ImportJobRepository,
    StagingQuestionRepository,
)

router = APIRouter()


def _repos(request: Request):
    db = request.app.state.db
    return (
        ImportJobRepository(db),
        StagingQuestionRepository(db),
        ImportedQuestionRepository(db),
    )


async def run_mistral_ocr_background(
    job_id: str,
    file_path: str,
    subject_id: str,
    source: str,
    user_id: str,
    job_repo: ImportJobRepository,
):
    try:
        import sys

        sys.path.append(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        )
        from scripts.mistral_ocr import MistralOCRPipeline

        pipeline = MistralOCRPipeline(
            file_path, subject_id, job_id=job_id, source=source
        )
        await pipeline.process_pdf()
        await job_repo.mark_completed(job_id, iso(now_utc()))
    except Exception as e:
        import logging

        logging.error(f"Mistral OCR pipeline failed for job {job_id}: {e}")
        await job_repo.mark_failed(job_id, str(e))
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
        addr = ipaddress.ip_address(
            socket.getaddrinfo(host, 80)[0][4][0]
        )
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise ValueError(
                "URL points to a private or local network address"
            )
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


@router.post("/import/pdf")
async def import_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    subject_id: str = Form(...),
    engine: str = Form("mistral"),
    source: str = Form(""),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    user=Depends(get_current_user),
):
    if not file and not url:
        return err("missing_input", "Must provide either a file or a URL", 400)

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
                return err(
                    "invalid_pdf",
                    "File does not appear to be a valid PDF",
                    400,
                )
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf", prefix=f"ocr_{job_id}_"
            )
            file_path = tmp.name
            tmp.write(contents)
            tmp.close()
            filename = (
                os.path.basename(file.filename or "file.pdf").replace(
                    "\x00", ""
                )
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

        await job_repo.create({
            "job_id": job_id,
            "user_id": user["user_id"],
            "filename": filename,
            "engine": "mistral",
            "source": source,
            "status": "PROCESSING",
            "progress": 0,
            "total_pages": 0,
            "created_at": iso(now_utc()),
        })

    except Exception as e:
        return err("upload_failed", str(e), 400)

    background_tasks.add_task(
        run_mistral_ocr_background,
        job_id,
        file_path,
        subject_id,
        source,
        user["user_id"],
        job_repo,
    )
    return ok({"job_id": job_id})


@router.get("/import/jobs")
async def list_import_jobs(
    request: Request,
    user=Depends(get_current_user),
):
    job_repo, _, _ = _repos(request)
    return ok(await job_repo.list_recent(user["user_id"]))


@router.delete("/import/jobs/{job_id}")
async def dismiss_import_job(
    job_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    job_repo, _, _ = _repos(request)
    await job_repo.delete(user["user_id"], job_id)
    return ok({"dismissed": 1})


@router.get("/staging")
async def list_staging_items(
    request: Request,
    user=Depends(get_current_user),
):
    _, staging_repo, _ = _repos(request)
    return ok(await staging_repo.list(user["user_id"]))


@router.delete("/staging/{staging_id}")
async def discard_staging_item(
    staging_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, staging_repo, _ = _repos(request)
    if await staging_repo.delete(user["user_id"], staging_id) == 0:
        return err("not_found", "Staging item not found", 404)
    return ok({"deleted": 1})


@router.delete("/staging")
async def clear_all_staging(
    request: Request,
    user=Depends(get_current_user),
):
    _, staging_repo, _ = _repos(request)
    return ok({"deleted": await staging_repo.clear_for_user(user["user_id"])})


@router.post("/staging/approve-specific")
async def approve_specific_item(
    request: Request,
    user=Depends(get_current_user),
):
    from pydantic import BaseModel, Field

    class ApproveSpecificRequest(BaseModel):
        staging_id: str = Field(max_length=50)

    body = ApproveSpecificRequest(**await request.json())
    _, staging_repo, imported_repo = _repos(request)
    item = await staging_repo.find(user["user_id"], body.staging_id)
    if not item:
        return err("not_found", "Staging item not found", 404)

    base_doc = {
        "user_id": user["user_id"],
        "subject_id": item["subject_id"],
        "topic_id": "TBD",
        "topic": item.get("topic", ""),
        "question_type": item.get("question_type", "MCQ"),
        "question_text": item.get("question_text", ""),
        "options": item.get("options", []),
        "correct_answer": item.get("correct_answer"),
        "solution": item.get("solution_text"),
        "source": item.get("source", ""),
        "tags": [item["topic"]] if item.get("topic") else [],
        "created_at": iso(now_utc()),
        "updated_at": iso(now_utc()),
    }

    if item.get("is_pyq"):
        pyq_doc = {
            **base_doc,
            "pyq_id": new_id("pyq"),
            "year": item.get("year", 0),
            "gate_set": item.get("gate_set"),
            "gate_qnum": item.get("gate_qnum"),
        }
        await imported_repo.create_pyq(pyq_doc)
    else:
        q_doc = {**base_doc, "question_id": new_id("q")}
        await imported_repo.create_question(q_doc)

    await staging_repo.delete_by_id(body.staging_id)
    return ok({"approved": 1})


@router.post("/staging/bulk-approve")
async def bulk_approve_staging_items(
    request: Request,
    user=Depends(get_current_user),
):
    _, staging_repo, imported_repo = _repos(request)
    ready_items = await staging_repo.list_ready(user["user_id"])

    if not ready_items:
        return err("no_items", "No ready items to approve", 400)

    questions_to_insert = []
    pyqs_to_insert = []
    staging_ids_to_delete = []

    for item in ready_items:
        base_doc = {
            "user_id": user["user_id"],
            "subject_id": item["subject_id"],
            "topic_id": "TBD",
            "topic": item.get("topic", ""),
            "question_type": item.get("question_type", "MCQ"),
            "question_text": item["question_text"],
            "options": item["options"],
            "correct_answer": item["correct_answer"],
            "solution": item["solution_text"],
            "source": item.get("source", ""),
            "tags": [item["topic"]] if item.get("topic") else [],
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc()),
        }

        if item.get("is_pyq"):
            pyqs_to_insert.append({
                **base_doc,
                "pyq_id": new_id("pyq"),
                "year": item.get("year", 0),
                "gate_set": item.get("gate_set"),
                "gate_qnum": item.get("gate_qnum"),
            })
        else:
            questions_to_insert.append({
                **base_doc,
                "question_id": new_id("q"),
            })

        staging_ids_to_delete.append(item["staging_id"])

    await imported_repo.create_questions(questions_to_insert)
    await imported_repo.create_pyqs(pyqs_to_insert)
    await staging_repo.delete_many_by_ids(staging_ids_to_delete)

    return ok({
        "approved": len(staging_ids_to_delete),
        "questions_added": len(questions_to_insert),
        "pyqs_added": len(pyqs_to_insert),
    })
