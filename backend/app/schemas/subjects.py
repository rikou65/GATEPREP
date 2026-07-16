from __future__ import annotations

from app.schemas.common import OutModel


class Subject(OutModel):
    subject_id: str
    name: str
    order: int = 0


class Topic(OutModel):
    topic_id: str
    subject_id: str
    name: str
    order: int = 0