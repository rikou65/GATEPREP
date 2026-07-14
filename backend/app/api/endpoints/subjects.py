from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.providers import get_subject_service
from app.api.responses import err, ok
from app.schemas.auth import CurrentUser
from app.schemas.common import Envelope
from app.schemas.subjects import Subject, Topic
from app.services.subjects import SubjectService

router = APIRouter()


@router.get("/subjects", response_model=Envelope[List[Subject]])
async def list_subjects(
    user: CurrentUser = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
):
    return ok(await service.list_subjects())


@router.get("/subjects/{subject_id}", response_model=Envelope[Subject])
async def get_subject(
    subject_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
):
    subject = await service.get_subject(subject_id)
    if not subject:
        return err("not_found", "Subject not found", 404)
    return ok(subject)


@router.get("/subjects/{subject_id}/topics", response_model=Envelope[List[Topic]])
async def list_topics(
    subject_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
):
    return ok(await service.list_topics(subject_id))


@router.get("/topics/{topic_id}", response_model=Envelope[dict])
async def get_topic(
    topic_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: SubjectService = Depends(get_subject_service),
):
    topic = await service.get_topic(topic_id)
    if not topic:
        return err("not_found", "Topic not found", 404)
    return ok(topic)
