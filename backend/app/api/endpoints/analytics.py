from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.providers import get_analytics_service
from app.api.responses import err, ok
from app.schemas.auth import CurrentUser
from app.schemas.common import Envelope
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/dashboard", response_model=Envelope[dict])
async def dashboard(
    user: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    return ok(await svc.get_dashboard(user.user_id))


@router.get("/analytics/subject/{subject_id}", response_model=Envelope[List[dict]])
async def subject_analytics(
    subject_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    return ok(await svc.get_subject_analytics(user.user_id, subject_id))


@router.get("/analytics/topic/{topic_id}", response_model=Envelope[dict])
async def topic_analytics(
    topic_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: AnalyticsService = Depends(get_analytics_service),
):
    result = await svc.get_topic_analytics(user.user_id, topic_id)
    if result is None:
        return err("not_found", "Topic not found", 404)
    return ok(result)
