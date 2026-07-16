from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.repositories.mistakes import MistakeRepository
from app.repositories.pyqs import PYQAttemptRepository, PYQRepository
from app.repositories.questions import (
    QuestionAttemptRepository,
    QuestionNoteRepository,
    QuestionRepository,
)
from app.schemas.practice import VALID_FLAG_TYPES


def is_correct(qtype: str, correct: Any, selected: Any) -> bool:
    if qtype == "MCQ":
        return str(selected) == str(correct)
    if qtype == "MSQ":
        return sorted([str(x) for x in (selected or [])]) == sorted(
            [str(x) for x in (correct or [])]
        )
    if qtype == "NAT":
        try:
            return abs(float(selected) - float(correct)) < 1e-3
        except Exception:
            return False
    return False


class QuestionService:
    def __init__(
        self,
        repo: QuestionRepository,
        att_repo: QuestionAttemptRepository,
        note_repo: QuestionNoteRepository,
        mistake_repo: MistakeRepository,
    ):
        self._repo = repo
        self._att_repo = att_repo
        self._note_repo = note_repo
        self._mistake_repo = mistake_repo

    async def list_questions(
        self, user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        question_type: Optional[str] = None,
        attempted: Optional[str] = None,
        result: Optional[str] = None,
        flag: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> Dict[str, Any]:
        docs = await self._repo.list_for_user(
            user_id,
            subject_id,
            topic_id,
            question_type,
            attempted,
            result,
            flag,
            limit,
            skip,
        )
        total = await self._repo.count_for_user(
            user_id,
            subject_id,
            topic_id,
            question_type,
            attempted,
            result,
            flag,
        )
        return {"items": docs, "total": total}

    async def get_question(self, question_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        q = await self._repo.find_by_id(question_id, user_id)
        if q is None:
            return None
        flags = await self._repo.get_flags(user_id, question_id)
        q["flags"] = flags
        return q

    async def create_question(self, question_id: str, user_id: str, body) -> Dict[str, Any]:
        doc = {
            "question_id": question_id,
            "user_id": user_id,
            **body.model_dump(),
            "created_at": iso(now_utc()),
        }
        await self._repo.create(doc)
        return doc

    async def update_question(
        self, user_id: str, question_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not updates:
            return {"error": "nothing_to_update"}
        updates["updated_at"] = iso(now_utc())
        matched = await self._repo.update(question_id, user_id, updates)
        if matched == 0:
            return None
        return await self._repo.find_by_id(question_id, user_id)

    async def delete_question(self, user_id: str, question_id: str) -> int:
        deleted = await self._repo.delete(question_id, user_id)
        if deleted == 0:
            return 0
        await self._att_repo.delete_all(user_id, question_id)
        await self._note_repo.delete_all(user_id, question_id)
        await self._repo.delete_flags(user_id, question_id)
        await self._mistake_repo.delete_all_for_question(user_id, question_id)
        return deleted


class QuestionAttemptService:
    def __init__(self, question_repo: QuestionRepository, attempt_repo: QuestionAttemptRepository):
        self._question_repo = question_repo
        self._attempt_repo = attempt_repo

    async def attempt(self, question_id: str, user_id: str, selected_answer: Any, time_taken: int) -> Optional[Dict[str, Any]]:
        q = await self._question_repo.find_by_id(question_id, user_id)
        if q is None:
            return None
        correct = is_correct(q["question_type"], q["correct_answer"], selected_answer)
        attempt = {
            "attempt_id": new_id("att"),
            "user_id": user_id,
            "question_id": question_id,
            "selected_answer": selected_answer,
            "is_correct": correct,
            "time_taken": time_taken,
            "attempted_at": iso(now_utc()),
        }
        await self._attempt_repo.create(attempt)
        return {"attempt": attempt, "correct_answer": q["correct_answer"], "solution": q["solution"]}

    async def list_attempts(self, question_id: str, user_id: str) -> list:
        return await self._attempt_repo.list_for_question(user_id, question_id)


class QuestionNoteService:
    def __init__(self, note_repo: QuestionNoteRepository):
        self._note_repo = note_repo

    async def get(self, question_id: str, user_id: str) -> Dict[str, Any]:
        n = await self._note_repo.find(user_id, question_id)
        return n or {"note_content": "", "question_id": question_id}

    async def save(self, question_id: str, user_id: str, content: str) -> None:
        await self._note_repo.upsert(user_id, question_id, content)


class QuestionFlagService:
    def __init__(self, repo: QuestionRepository):
        self._repo = repo

    async def add(self, question_id: str, user_id: str, flag_type: str) -> Optional[str]:
        if flag_type not in VALID_FLAG_TYPES:
            return f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}"
        q = await self._repo.find_by_id(question_id, user_id)
        if q is None:
            return "Question not found"
        now = iso(now_utc())
        await self._repo.add_flag({
            "user_id": user_id,
            "question_id": question_id,
            "flag_type": flag_type,
            "created_at": now,
            "updated_at": now,
        })
        return None

    async def remove(self, question_id: str, user_id: str, flag_type: str) -> Optional[str]:
        if flag_type not in VALID_FLAG_TYPES:
            return f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}"
        await self._repo.remove_flag(user_id, question_id, flag_type)
        return None

    async def list(self, question_id: str, user_id: str) -> list:
        return await self._repo.get_flags(user_id, question_id)


class PYQService:
    def __init__(
        self,
        repo: PYQRepository,
        att_repo: PYQAttemptRepository,
    ):
        self._repo = repo
        self._att_repo = att_repo

    async def list_pyqs(
        self, user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        year: Optional[int] = None,
        attempted: Optional[str] = None,
        result: Optional[str] = None,
        flag: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> Dict[str, Any]:
        docs = await self._repo.list_for_user(
            user_id,
            subject_id,
            topic_id,
            year,
            attempted,
            result,
            flag,
            limit,
            skip,
        )
        total = await self._repo.count_for_user(
            user_id,
            subject_id,
            topic_id,
            year,
            attempted,
            result,
            flag,
        )
        return {"items": docs, "total": total}

    async def create_pyq(self, pyq_id: str, user_id: str, body) -> Dict[str, Any]:
        doc = {
            "pyq_id": pyq_id,
            "user_id": user_id,
            **body.model_dump(),
            "created_at": iso(now_utc()),
        }
        await self._repo.create(doc)
        return doc

    async def update_pyq(
        self, user_id: str, pyq_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not updates:
            return {"error": "nothing_to_update"}
        updates["updated_at"] = iso(now_utc())
        matched = await self._repo.update(pyq_id, user_id, updates)
        if matched == 0:
            return None
        return await self._repo.find_by_id(pyq_id, user_id)

    async def delete_pyq(self, user_id: str, pyq_id: str) -> int:
        deleted = await self._repo.delete(pyq_id, user_id)
        if deleted == 0:
            return 0
        await self._att_repo.delete_all(user_id, pyq_id)
        await self._repo.delete_flags(user_id, pyq_id)
        return deleted

    async def add_flag(
        self, user_id: str, pyq_id: str, flag_type: str
    ) -> Optional[str]:
        if flag_type not in VALID_FLAG_TYPES:
            return f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}"
        p = await self._repo.find_by_id(pyq_id, user_id)
        if p is None:
            return "PYQ not found"
        now = iso(now_utc())
        await self._repo.add_flag({
            "user_id": user_id, "pyq_id": pyq_id,
            "flag_type": flag_type, "created_at": now, "updated_at": now,
        })
        return None

    async def remove_flag(
        self, user_id: str, pyq_id: str, flag_type: str
    ) -> Optional[str]:
        if flag_type not in VALID_FLAG_TYPES:
            return f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}"
        await self._repo.remove_flag(user_id, pyq_id, flag_type)
        return None

    async def list_flags(self, user_id: str, pyq_id: str) -> list:
        return await self._repo.get_flags(user_id, pyq_id)


class PYQAttemptService:
    def __init__(self, pyq_repo: PYQRepository, attempt_repo: PYQAttemptRepository):
        self._pyq_repo = pyq_repo
        self._attempt_repo = attempt_repo

    async def attempt(self, pyq_id: str, user_id: str, selected_answer: Any, time_taken: int) -> Optional[Dict[str, Any]]:
        p = await self._pyq_repo.find_by_id(pyq_id, user_id)
        if p is None:
            return None
        correct = is_correct(p["question_type"], p["correct_answer"], selected_answer)
        attempt = {
            "attempt_id": new_id("att"),
            "user_id": user_id,
            "pyq_id": pyq_id,
            "selected_answer": selected_answer,
            "is_correct": correct,
            "time_taken": time_taken,
            "attempted_at": iso(now_utc()),
        }
        await self._attempt_repo.create(attempt)
        return {"attempt": attempt, "correct_answer": p["correct_answer"], "solution": p["solution"]}

    async def list_attempts(self, pyq_id: str, user_id: str) -> list:
        return await self._attempt_repo.list_for_pyq(user_id, pyq_id)


class MistakeService:
    def __init__(self, repo: MistakeRepository):
        self._repo = repo

    async def list_mistakes(
        self, user_id: str,
        subject_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        mistake_type: Optional[str] = None,
    ) -> list:
        return await self._repo.list_for_user(
            user_id,
            subject_id,
            topic_id,
            mistake_type,
        )

    async def create_mistake(self, user_id: str, question_id: str, mistake_type: str, note: str) -> Optional[Dict[str, Any]]:
        q = await self._repo.find_question(question_id, user_id)
        if q is None:
            return None
        doc = {
            "mistake_id": new_id("mis"),
            "user_id": user_id,
            "question_id": question_id,
            "subject_id": q["subject_id"],
            "topic_id": q["topic_id"],
            "mistake_type": mistake_type,
            "note": note or "",
            "created_at": iso(now_utc()),
        }
        await self._repo.create(doc)
        return doc

    async def delete_mistake(self, mistake_id: str, user_id: str) -> int:
        return await self._repo.delete(mistake_id, user_id)
