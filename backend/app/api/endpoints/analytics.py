from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.repositories.analytics import AnalyticsRepository
from app.services.analytics import AnalyticsService

router = APIRouter()


def _get_service(request: Request) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(request.app.state.db))


@router.get("/dashboard")
async def dashboard(
    request: Request,
    user=Depends(get_current_user),
):
    svc = _get_service(request)
    return ok(await svc.get_dashboard(user["user_id"]))


@router.get("/analytics/subject/{subject_id}")
async def subject_analytics(
    subject_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    svc = _get_service(request)
    return ok(
        await svc.get_subject_analytics(user["user_id"], subject_id)
    )


@router.get("/analytics/topic/{topic_id}")
async def topic_analytics(
    topic_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    svc = _get_service(request)
    result = await svc.get_topic_analytics(user["user_id"], topic_id)
    if result is None:
        return err("not_found", "Topic not found", 404)
    return ok(result)
