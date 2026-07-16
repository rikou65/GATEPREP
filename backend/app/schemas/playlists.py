from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PlaylistImportIn(BaseModel):
    youtube_url: str = Field(max_length=500)
    subject_id: str = Field(max_length=50)


class VideoProgressIn(BaseModel):
    watch_percentage: float = Field(ge=0, le=100)
    watch_time: int = Field(default=0, ge=0)
    completed: Optional[bool] = None


class VideoNotesIn(BaseModel):
    note_content: str = Field(max_length=50000)