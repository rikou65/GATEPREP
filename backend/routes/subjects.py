"""Subject and topic routes for GATEPREP."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from shared import db, err, get_current_user, ok

router = APIRouter()


@router.get("/subjects")
async def list_subjects(user=Depends(get_current_user)):
    docs = await db.subjects.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return ok(docs)


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: str, user=Depends(get_current_user)):
    s = await db.subjects.find_one({"subject_id": subject_id}, {"_id": 0})
    if not s:
        return err("not_found", "Subject not found", 404)
    return ok(s)


@router.get("/subjects/{subject_id}/topics")
async def list_topics(subject_id: str, user=Depends(get_current_user)):
    docs = await db.topics.find({"subject_id": subject_id}, {"_id": 0}).sort("order", 1).to_list(500)
    return ok(docs)


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str, user=Depends(get_current_user)):
    t = await db.topics.find_one({"topic_id": topic_id}, {"_id": 0})
    if not t:
        return err("not_found", "Topic not found", 404)
    s = await db.subjects.find_one({"subject_id": t["subject_id"]}, {"_id": 0})
    t["subject"] = s
    return ok(t)
