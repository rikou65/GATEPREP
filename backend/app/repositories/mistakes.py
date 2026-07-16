from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.practice_queries import build_mistake_list_pipeline


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

    async def list_for_user(
        self,
        user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        mistake_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        pipeline = build_mistake_list_pipeline(
            user_id,
            subject_id,
            topic_id,
            mistake_type,
        )
        return await self._db.mistakes.aggregate(pipeline).to_list(500)

    async def find_question(self, question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.questions.find_one(
            {"question_id": question_id, "user_id": user_id}, {"_id": 0}
        )
