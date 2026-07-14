from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import OutModel


class ResourceIn(BaseModel):
    subject_id: str = Field(max_length=50)
    resource_type: str = Field(max_length=50)
    title: str = Field(max_length=500)
    external_url: Optional[str] = Field(default="", max_length=2000)
    file_size: Optional[int] = Field(default=0, ge=0)


class ResourceNotesIn(BaseModel):
    content: Optional[str] = Field(default=None, max_length=50000)
    important_pages: Optional[List[Any]] = None


class TogglePageIn(BaseModel):
    page: int
    label: Optional[str] = Field(default="", max_length=200)


class PageLabelIn(BaseModel):
    page: int
    label: str = Field(max_length=200)