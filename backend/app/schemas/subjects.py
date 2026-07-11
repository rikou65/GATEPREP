from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Subject(BaseModel):
    subject_id: str
    name: str
    order: int = 0


class Topic(BaseModel):
    topic_id: str
    subject_id: str
    name: str
    order: int = 0
