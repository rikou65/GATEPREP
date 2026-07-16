from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.repositories.staging import (
    ImportedQuestionRepository,
    ImportJobRepository,
    StagingQuestionRepository,
)


class StagingService:
    """Business logic for the OCR staging approval flow.

    Endpoints stay transport-only: they validate the request, call these
    methods, and translate the result into HTTP. Ownership checks happen
    here (every read is scoped by ``user_id``).
    """

    def __init__(
        self,
        staging_repo: StagingQuestionRepository,
        imported_repo: ImportedQuestionRepository,
        import_job_repo: ImportJobRepository,
    ):
        self._staging = staging_repo
        self._imported = imported_repo
        self._jobs = import_job_repo

    async def create_import_job(self, doc: Dict[str, Any]) -> None:
        await self._jobs.create(doc)

    async def mark_import_completed(self, job_id: str) -> None:
        await self._jobs.mark_completed(job_id, iso(now_utc()))

    async def mark_import_failed(self, job_id: str, error: str) -> None:
        await self._jobs.mark_failed(job_id, error)

    async def list_import_jobs(self, user_id: str) -> list:
        return await self._jobs.list_recent(user_id)

    async def dismiss_import_job(self, user_id: str, job_id: str) -> int:
        return await self._jobs.delete(user_id, job_id)

    async def list_staging_items(self, user_id: str) -> list:
        return await self._staging.list(user_id)

    async def discard_staging_item(self, user_id: str, staging_id: str) -> int:
        return await self._staging.delete(user_id, staging_id)

    async def clear_staging(self, user_id: str) -> int:
        return await self._staging.clear_for_user(user_id)

    async def approve_specific(
        self, user_id: str, staging_id: str
    ) -> Optional[Dict[str, Any]]:
        """Approve a single staging item into the live question bank.

        Returns ``{"approved": 1}`` on success, or ``None`` when the item
        does not exist for this user (caller returns 404).
        """
        item = await self._staging.find(user_id, staging_id)
        if not item:
            return None

        doc = self._build_live_doc(user_id, item)
        if "pyq_id" in doc:
            await self._imported.create_pyq(doc)
        else:
            await self._imported.create_question(doc)
        await self._staging.delete_by_id(staging_id)
        return {"approved": 1}

    async def bulk_approve(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Approve every READY staging item for this user.

        Returns counts of approved items and the questions/pyqs created, or
        ``None`` when there are no ready items (caller returns 400).
        """
        ready_items = await self._staging.list_ready(user_id)
        if not ready_items:
            return None

        live_docs: list[Dict[str, Any]] = []
        for item in ready_items:
            live_docs.append(self._build_live_doc(user_id, item))

        questions = [d for d in live_docs if "question_id" in d]
        pyqs = [d for d in live_docs if "pyq_id" in d]
        await self._imported.create_questions(questions)
        await self._imported.create_pyqs(pyqs)

        staging_ids = [item["staging_id"] for item in ready_items]
        await self._staging.delete_many_by_ids(staging_ids)

        return {
            "approved": len(staging_ids),
            "questions_added": len(questions),
            "pyqs_added": len(pyqs),
        }

    def _build_live_doc(
        self, user_id: str, item: Dict[str, Any]
    ) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "user_id": user_id,
            "subject_id": item["subject_id"],
            "topic_id": "TBD",
            "topic": item.get("topic", ""),
            "question_type": item.get("question_type", "MCQ"),
            "question_text": item.get("question_text", ""),
            "options": item.get("options", []),
            "correct_answer": item.get("correct_answer"),
            "solution": item.get("solution_text"),
            "source": item.get("source", ""),
            "tags": [item["topic"]] if item.get("topic") else [],
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc()),
        }
        if item.get("is_pyq"):
            base.update({
                "pyq_id": new_id("pyq"),
                "year": item.get("year", 0),
                "gate_set": item.get("gate_set"),
                "gate_qnum": item.get("gate_qnum"),
            })
        else:
            base["question_id"] = new_id("q")
        return base
