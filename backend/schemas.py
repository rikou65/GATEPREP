"""Shared Pydantic schemas for GATEPREP."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AttemptIn(BaseModel):
    selected_answer: Any
    time_taken: int = 0


class NotesIn(BaseModel):
    note_content: str


class QuestionIn(BaseModel):
    subject_id: str
    topic_id: str
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: Any
    solution: str
    source: str = "User"
    year: Optional[int] = None


class QuestionPatch(BaseModel):
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Any = None
    solution: Optional[str] = None
    source: Optional[str] = None
    year: Optional[int] = None
    gate_set: Optional[str] = None
    gate_qnum: Optional[str] = None


class PYQIn(QuestionIn):
    year: int
    gate_set: Optional[str] = None
    gate_qnum: Optional[str] = None


class FlagIn(BaseModel):
    flag_type: str


class MistakeIn(BaseModel):
    question_id: str
    mistake_type: str
    note: Optional[str] = ""


class ApproveSpecificRequest(BaseModel):
    staging_id: str


class PlaylistImportIn(BaseModel):
    youtube_url: str
    subject_id: str


class VideoProgressIn(BaseModel):
    watch_percentage: float
    watch_time: int = 0


class VideoNotesIn(BaseModel):
    note_content: str


class ResourceIn(BaseModel):
    subject_id: str
    resource_type: str
    title: str
    external_url: Optional[str] = ""
    file_size: Optional[int] = 0


class ResourceNotesIn(BaseModel):
    content: Optional[str] = None
    important_pages: Optional[List[Any]] = None


class TogglePageIn(BaseModel):
    page: int
    label: Optional[str] = ""


class PageLabelIn(BaseModel):
    page: int
    label: str = ""
