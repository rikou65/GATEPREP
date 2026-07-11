from __future__ import annotations

from typing import Any, Dict, List, Optional


class MistakeRepository:
    def __init__(self, db):
        self._db = db

    async def create(self, doc: Dict[str, Any]) -> None:
        await self._db.mistakes.insert_one(dict(doc))

    async def delete(self, mistake_id: str, user_id: str) -> int:
        r = await self._db.mistakes.delete_one(
            {"mistake_id": mistake_id, "user_id": user_id}
        )
        return r.deleted_count

    async def delete_all_for_question(self, user_id: str, question_id: str) -> None:
        await self._db.mistakes.delete_many(
            {"user_id": user_id, "question_id": question_id}
        )

    async def list_with_aggregation(
        self, pipeline: List[Dict[str, Any]], limit: int = 500
    ) -> List[Dict[str, Any]]:
        return await self._db.mistakes.aggregate(pipeline).to_list(limit)

    async def find_question(self, question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.questions.find_one(
            {"question_id": question_id, "user_id": user_id}, {"_id": 0}
        )
