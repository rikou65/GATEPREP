from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.repositories.subjects import SubjectRepository
from app.services.subjects import SubjectService

router = APIRouter()


def _get_service(request: Request):
    db = request.app.state.db
    return SubjectService(SubjectRepository(db))


@router.get("/subjects")
async def list_subjects(
    request: Request,
    user=Depends(get_current_user),
):
    service = _get_service(request)
    return ok(await service.list_subjects())


@router.get("/subjects/{subject_id}")
async def get_subject(
    subject_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    service = _get_service(request)
    subject = await service.get_subject(subject_id)
    if not subject:
        return err("not_found", "Subject not found", 404)
    return ok(subject)


@router.get("/subjects/{subject_id}/topics")
async def list_topics(
    subject_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    service = _get_service(request)
    return ok(await service.list_topics(subject_id))


@router.get("/topics/{topic_id}")
async def get_topic(
    topic_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    service = _get_service(request)
    topic = await service.get_topic(topic_id)
    if not topic:
        return err("not_found", "Topic not found", 404)
    return ok(topic)
