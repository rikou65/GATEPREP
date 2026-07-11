from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.subjects import SubjectRepository


class SubjectService:
    def __init__(self, repo: SubjectRepository):
        self._repo = repo

    async def list_subjects(self) -> List[Dict[str, Any]]:
        return await self._repo.list_all()

    async def get_subject(self, subject_id: str) -> Optional[Dict[str, Any]]:
        return await self._repo.find_by_id(subject_id)

    async def list_topics(self, subject_id: str) -> List[Dict[str, Any]]:
        return await self._repo.list_topics(subject_id)

    async def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        topic = await self._repo.find_topic_by_id(topic_id)
        if topic is None:
            return None
        subject = await self._repo.find_by_id(topic["subject_id"])
        if subject:
            topic["subject"] = subject
        return topic
