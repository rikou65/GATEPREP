from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, File, Form, Request
from pydantic import BaseModel

from shared import db, err, get_current_user, ok, new_id, iso, now_utc, logger
from limiter import limiter

router = APIRouter()

async def run_mistral_ocr_background(job_id: str, file_path: str, subject_id: str, source: str = ""):
    """Background task to run the Mistral OCR pipeline."""
    try:
        import sys
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from scripts.mistral_ocr import MistralOCRPipeline

        pipeline = MistralOCRPipeline(file_path, subject_id, job_id=job_id, source=source)
        await pipeline.process_pdf()
        await db.import_jobs.update_one({"job_id": job_id}, {"$set": {"status": "COMPLETED", "completed_at": iso(now_utc())}})
    except Exception as e:
        logger.error(f"Mistral OCR pipeline failed for job {job_id}: {e}")
        await db.import_jobs.update_one({"job_id": job_id}, {"$set": {"status": "FAILED", "error": str(e)}})
    finally:
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

@router.post("/import/pdf")
@limiter.limit("10/minute")
async def import_pdf(
    request: Request,
    background_tasks: BackgroundTasks,
    subject_id: str = Form(...),
    engine: str = Form("mistral"),
    source: str = Form(""),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    user=Depends(get_current_user)
):
    if not file and not url:
        return err("missing_input", "Must provide either a file or a URL", 400)
    
    job_id = new_id("job")
    file_path = f"temp_{job_id}.pdf"
    
    try:
        if file:
            contents = await file.read()
            with open(file_path, "wb") as f: f.write(contents)
            filename = file.filename
        elif url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30)
                resp.raise_for_status()
                with open(file_path, "wb") as f: f.write(resp.content)
            filename = url.split("/")[-1] or "remote_file.pdf"
            
        await db.import_jobs.insert_one({
            "job_id": job_id, "user_id": user["user_id"], "filename": filename,
            "engine": "mistral",
            "source": source,
            "status": "PROCESSING", "progress": 0, "total_pages": 0,
            "created_at": iso(now_utc())
        })
        
    except Exception as e:
        return err("upload_failed", str(e), 400)

    # Always use Mistral OCR pipeline
    background_tasks.add_task(run_mistral_ocr_background, job_id, file_path, subject_id, source)
        
    return ok({"job_id": job_id})

@router.get("/import/jobs")
async def list_import_jobs(user=Depends(get_current_user)):
    """Fetch recent import jobs to show progress bars."""
    docs = await db.import_jobs.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
    return ok(docs)

@router.delete("/import/jobs/{job_id}")
async def dismiss_import_job(job_id: str, user=Depends(get_current_user)):
    """Permanently delete an import job record (dismiss error from UI)."""
    await db.import_jobs.delete_one({"job_id": job_id, "user_id": user["user_id"]})
    return ok({"dismissed": 1})

@router.get("/staging")
async def list_staging_items(user=Depends(get_current_user)):
    """Fetch all items currently in the staging queue for review."""
    docs = await db.staging_questions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return ok(docs)

@router.delete("/staging/{staging_id}")
async def discard_staging_item(staging_id: str, user=Depends(get_current_user)):
    """Discard a specific item from the staging queue."""
    r = await db.staging_questions.delete_one({"staging_id": staging_id})
    if r.deleted_count == 0:
        return err("not_found", "Staging item not found", 404)
    return ok({"deleted": 1})

@router.delete("/staging")
async def clear_all_staging(user=Depends(get_current_user)):
    """Wipe the entire staging queue. Use before re-ingesting a corrected PDF."""
    result = await db.staging_questions.delete_many({})
    return ok({"deleted": result.deleted_count})

class ApproveSpecificRequest(BaseModel):
    staging_id: str

@router.post("/staging/approve-specific")
async def approve_specific_item(
    req: ApproveSpecificRequest,
    user=Depends(get_current_user)
):
    """Manually approve a specific item (even if it's orphaned or missing data)."""
    item = await db.staging_questions.find_one({"staging_id": req.staging_id})
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
        "tags": ([item["topic"]] if item.get("topic") else []),
        "created_at": iso(now_utc()),
        "updated_at": iso(now_utc())
    }
    
    if item.get("is_pyq"):
        pyq_doc = {
            **base_doc,
            "pyq_id": new_id("pyq"),
            "year": item.get("year", 0),
            "gate_set": item.get("gate_set"),
            "gate_qnum": item.get("gate_qnum")
        }
        await db.pyqs.insert_one(pyq_doc)
    else:
        q_doc = {
            **base_doc,
            "question_id": new_id("q")
        }
        await db.questions.insert_one(q_doc)
        
    await db.staging_questions.delete_one({"staging_id": req.staging_id})
    return ok({"approved": 1})

@router.post("/staging/bulk-approve")
async def bulk_approve_staging_items(user=Depends(get_current_user)):
    """Move all 'READY' items from staging to the live databases (questions or pyqs)."""
    # 1. Fetch all READY items
    ready_items = await db.staging_questions.find({"status": "READY"}, {"_id": 0}).to_list(10000)
    
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
            "tags": ([item["topic"]] if item.get("topic") else []),
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc())
        }
        
        if item.get("is_pyq"):
            pyqs_to_insert.append({
                **base_doc,
                "pyq_id": new_id("pyq"),
                "year": item.get("year", 0),
                "gate_set": item.get("gate_set"),
                "gate_qnum": item.get("gate_qnum")
            })
        else:
            questions_to_insert.append({
                **base_doc,
                "question_id": new_id("q")
            })
            
        staging_ids_to_delete.append(item["staging_id"])
        
    # 2. Insert into live collections
    if questions_to_insert:
        await db.questions.insert_many(questions_to_insert)
    if pyqs_to_insert:
        await db.pyqs.insert_many(pyqs_to_insert)
        
    # 3. Cleanup staging
    await db.staging_questions.delete_many({"staging_id": {"$in": staging_ids_to_delete}})
    
    return ok({
        "approved": len(staging_ids_to_delete),
        "questions_added": len(questions_to_insert),
        "pyqs_added": len(pyqs_to_insert)
    })
