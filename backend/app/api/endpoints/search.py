from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.api.providers import get_search_service
from app.api.responses import ok
from app.schemas.auth import CurrentUser
from app.schemas.common import Envelope
from app.schemas.search import SearchResultOut
from app.services.search import SearchService

router = APIRouter()


@router.get("/search", response_model=Envelope[List[SearchResultOut]])
async def global_search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=12, ge=1, le=40),
    user: CurrentUser = Depends(get_current_user),
    svc: SearchService = Depends(get_search_service),
):
    return ok(await svc.search(user.user_id, q, limit))
