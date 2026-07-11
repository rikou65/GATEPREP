from __future__ import annotations

from typing import Any, Dict, List


class ImportJobRepository:
    def __init__(self, db):
        self._db = db

    async def create(self, doc: Dict[str, Any]) -> None:
        await self._db.import_jobs.insert_one(dict(doc))

    async def mark_completed(self, job_id: str, completed_at: str) -> None:
        await self._db.import_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "COMPLETED", "completed_at": completed_at}},
        )

    async def mark_failed(self, job_id: str, error: str) -> None:
        await self._db.import_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "FAILED", "error": error}},
        )

    async def list_recent(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return (
            await self._db.import_jobs.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
            .to_list(limit)
        )

    async def delete(self, user_id: str, job_id: str) -> int:
        result = await self._db.import_jobs.delete_one(
            {"job_id": job_id, "user_id": user_id}
        )
        return result.deleted_count


class StagingQuestionRepository:
    def __init__(self, db):
        self._db = db

    async def list(self, user_id: str) -> List[Dict[str, Any]]:
        return (
            await self._db.staging_questions.find(
                {"user_id": user_id}, {"_id": 0}
            )
            .sort("created_at", -1)
            .to_list(500)
        )

    async def list_ready(self, user_id: str) -> List[Dict[str, Any]]:
        return await self._db.staging_questions.find(
            {"status": "READY", "user_id": user_id},
            {"_id": 0},
        ).to_list(500)

    async def find(self, user_id: str, staging_id: str) -> Dict[str, Any] | None:
        return await self._db.staging_questions.find_one(
            {"staging_id": staging_id, "user_id": user_id},
            {"_id": 0},
        )

    async def delete(self, user_id: str, staging_id: str) -> int:
        result = await self._db.staging_questions.delete_one(
            {"staging_id": staging_id, "user_id": user_id}
        )
        return result.deleted_count

    async def delete_by_id(self, staging_id: str) -> None:
        await self._db.staging_questions.delete_one({"staging_id": staging_id})

    async def delete_many_by_ids(self, staging_ids: List[str]) -> None:
        await self._db.staging_questions.delete_many(
            {"staging_id": {"$in": staging_ids}}
        )

    async def clear_for_user(self, user_id: str) -> int:
        result = await self._db.staging_questions.delete_many(
            {"user_id": user_id}
        )
        return result.deleted_count


class ImportedQuestionRepository:
    def __init__(self, db):
        self._db = db

    async def create_question(self, doc: Dict[str, Any]) -> None:
        await self._db.questions.insert_one(dict(doc))

    async def create_pyq(self, doc: Dict[str, Any]) -> None:
        await self._db.pyqs.insert_one(dict(doc))

    async def create_questions(self, docs: List[Dict[str, Any]]) -> None:
        if docs:
            await self._db.questions.insert_many([dict(doc) for doc in docs])

    async def create_pyqs(self, docs: List[Dict[str, Any]]) -> None:
        if docs:
            await self._db.pyqs.insert_many([dict(doc) for doc in docs])
