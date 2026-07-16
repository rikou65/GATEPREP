from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.practice_queries import (
    build_question_count_pipeline,
    build_question_list_pipeline,
)


class QuestionRepository:
    def __init__(self, db):
        self._db = db

    async def find_by_id(self, question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.questions.find_one(
            {"question_id": question_id, "user_id": user_id}, {"_id": 0}
        )

    async def create(self, doc: Dict[str, Any]) -> None:
        await self._db.questions.insert_one(dict(doc))

    async def update(self, question_id: str, user_id: str, updates: Dict[str, Any]) -> int:
        r = await self._db.questions.update_one(
            {"question_id": question_id, "user_id": user_id},
            {"$set": updates},
        )
        return r.matched_count

    async def delete(self, question_id: str, user_id: str) -> int:
        r = await self._db.questions.delete_one(
            {"question_id": question_id, "user_id": user_id}
        )
        return r.deleted_count

    async def list_for_user(
        self,
        user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        question_type: Optional[str] = None,
        attempted: Optional[str] = None,
        result: Optional[str] = None,
        flag: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        pipeline = build_question_list_pipeline(
            user_id,
            subject_id,
            topic_id,
            question_type,
            attempted,
            result,
            flag,
            skip,
            limit,
        )
        return await self._db.questions.aggregate(pipeline).to_list(limit)

    async def count_for_user(
        self,
        user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        question_type: Optional[str] = None,
        attempted: Optional[str] = None,
        result: Optional[str] = None,
        flag: Optional[str] = None,
    ) -> int:
        pipeline = build_question_count_pipeline(
            user_id,
            subject_id,
            topic_id,
            question_type,
            attempted,
            result,
            flag,
        )
        docs = await self._db.questions.aggregate(pipeline).to_list(1)
        return docs[0]["total"] if docs else 0

    async def get_flags(self, user_id: str, question_id: str) -> List[str]:
        flags = await self._db.question_flags.find(
            {"user_id": user_id, "question_id": question_id},
            {"_id": 0, "flag_type": 1},
        ).to_list(10)
        return [f["flag_type"] for f in flags]

    async def add_flag(self, doc: Dict[str, Any]) -> None:
        await self._db.question_flags.update_one(
            {
                "user_id": doc["user_id"],
                "question_id": doc["question_id"],
                "flag_type": doc["flag_type"],
            },
            {"$set": {"updated_at": doc.get("updated_at", "")},
             "$setOnInsert": {
                 "user_id": doc["user_id"],
                 "question_id": doc["question_id"],
                 "flag_type": doc["flag_type"],
                 "created_at": doc.get("created_at", ""),
             }},
            upsert=True,
        )

    async def remove_flag(self, user_id: str, question_id: str, flag_type: str) -> None:
        await self._db.question_flags.delete_one(
            {"user_id": user_id, "question_id": question_id, "flag_type": flag_type}
        )

    async def delete_flags(self, user_id: str, question_id: str) -> None:
        await self._db.question_flags.delete_many(
            {"user_id": user_id, "question_id": question_id}
        )


class QuestionAttemptRepository:
    def __init__(self, db):
        self._db = db

    async def create(self, doc: Dict[str, Any]) -> None:
        await self._db.question_attempts.insert_one(dict(doc))

    async def list_for_question(self, user_id: str, question_id: str) -> List[Dict[str, Any]]:
        return await self._db.question_attempts.find(
            {"user_id": user_id, "question_id": question_id}, {"_id": 0}
        ).sort("attempted_at", -1).to_list(200)

    async def delete_all(self, user_id: str, question_id: str) -> None:
        await self._db.question_attempts.delete_many(
            {"user_id": user_id, "question_id": question_id}
        )


class QuestionNoteRepository:
    def __init__(self, db):
        self._db = db

    async def find(self, user_id: str, question_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.question_notes.find_one(
            {"user_id": user_id, "question_id": question_id}, {"_id": 0}
        )

    async def upsert(self, user_id: str, question_id: str, content: str) -> None:
        from app.core.ids import new_id
        from app.core.time import iso, now_utc

        await self._db.question_notes.update_one(
            {"user_id": user_id, "question_id": question_id},
            {
                "$set": {"note_content": content, "updated_at": iso(now_utc())},
                "$setOnInsert": {
                    "note_id": new_id("note"),
                    "user_id": user_id,
                    "question_id": question_id,
                    "created_at": iso(now_utc()),
                },
            },
            upsert=True,
        )

    async def delete_all(self, user_id: str, question_id: str) -> None:
        await self._db.question_notes.delete_many(
            {"user_id": user_id, "question_id": question_id}
        )
