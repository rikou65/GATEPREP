"""Shared Pydantic schemas for GATEPREP."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AttemptIn(BaseModel):
    selected_answer: Any
    time_taken: int = Field(default=0, ge=0)


class NotesIn(BaseModel):
    note_content: str = Field(max_length=50000)


class QuestionIn(BaseModel):
    subject_id: str = Field(max_length=50)
    topic_id: str = Field(max_length=50)
    question_type: str = Field(max_length=10)
    question_text: str = Field(max_length=10000)
    options: Optional[List[str]] = None
    correct_answer: Any
    solution: str = Field(max_length=50000)
    source: str = Field(default="User", max_length=50)
    year: Optional[int] = None


class QuestionPatch(BaseModel):
    subject_id: Optional[str] = Field(default=None, max_length=50)
    topic_id: Optional[str] = Field(default=None, max_length=50)
    question_type: Optional[str] = Field(default=None, max_length=10)
    question_text: Optional[str] = Field(default=None, max_length=10000)
    options: Optional[List[str]] = None
    correct_answer: Any = None
    solution: Optional[str] = Field(default=None, max_length=50000)
    source: Optional[str] = Field(default=None, max_length=50)
    year: Optional[int] = None
    gate_set: Optional[str] = Field(default=None, max_length=10)
    gate_qnum: Optional[str] = Field(default=None, max_length=10)


class PYQIn(QuestionIn):
    year: int = Field(ge=1980, le=2030)
    gate_set: Optional[str] = Field(default=None, max_length=10)
    gate_qnum: Optional[str] = Field(default=None, max_length=10)


class FlagIn(BaseModel):
    flag_type: str = Field(max_length=20)


class MistakeIn(BaseModel):
    question_id: str = Field(max_length=50)
    mistake_type: str = Field(max_length=50)
    note: Optional[str] = Field(default="", max_length=5000)


class ApproveSpecificRequest(BaseModel):
    staging_id: str = Field(max_length=50)


class PlaylistImportIn(BaseModel):
    youtube_url: str = Field(max_length=500)
    subject_id: str = Field(max_length=50)


class VideoProgressIn(BaseModel):
    watch_percentage: float = Field(ge=0, le=100)
    watch_time: int = Field(default=0, ge=0)


class VideoNotesIn(BaseModel):
    note_content: str = Field(max_length=50000)


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
    page: int = Field(ge=1)
    label: Optional[str] = Field(default="", max_length=200)


class PageLabelIn(BaseModel):
    page: int = Field(ge=1)
    label: str = Field(max_length=200)
