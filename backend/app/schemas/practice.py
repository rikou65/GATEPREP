from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import FlagsOut, OutModel

VALID_FLAG_TYPES = {"review", "important"}


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


class PracticeListOut(OutModel):
    items: List[Dict[str, Any]]
    total: int


class AttemptResultOut(OutModel):
    attempt: Dict[str, Any]
    correct_answer: Any
    solution: Optional[str] = None


class QuestionNotesOut(OutModel):
    note_content: str = ""
    question_id: str