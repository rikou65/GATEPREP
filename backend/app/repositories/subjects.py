from __future__ import annotations

from typing import Any, Dict, List, Optional


class SubjectRepository:
    def __init__(self, db):
        self._db = db

    async def list_all(self) -> List[Dict[str, Any]]:
        return (
            await self._db.subjects.find({}, {"_id": 0})
            .sort("order", 1)
            .to_list(100)
        )

    async def find_by_id(self, subject_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.subjects.find_one(
            {"subject_id": subject_id}, {"_id": 0}
        )

    async def list_topics(self, subject_id: str) -> List[Dict[str, Any]]:
        return (
            await self._db.topics.find({"subject_id": subject_id}, {"_id": 0})
            .sort("order", 1)
            .to_list(500)
        )

    async def find_topic_by_id(self, topic_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.topics.find_one(
            {"topic_id": topic_id}, {"_id": 0}
        )
