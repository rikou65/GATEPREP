from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.repositories.questions import QuestionRepository, QuestionAttemptRepository, QuestionNoteRepository
from app.repositories.pyqs import PYQRepository, PYQAttemptRepository
from app.repositories.mistakes import MistakeRepository
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


def build_question_list_pipeline(
    user_id: str,
    subject_id: Optional[str],
    topic_id: Optional[str],
    question_type: Optional[str],
    attempted: Optional[str],
    result: Optional[str],
    flag: Optional[str],
    skip: int,
    limit: int,
) -> list:
    match_q: Dict[str, Any] = {"user_id": user_id}
    if subject_id:
        match_q["subject_id"] = subject_id
    if topic_id:
        match_q["topic_id"] = topic_id
    if question_type:
        match_q["question_type"] = question_type

    pipeline: List[Dict[str, Any]] = [
        {"$match": match_q},
        {"$lookup": {
            "from": "question_attempts",
            "let": {"qid": "$question_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$question_id", "$$qid"]},
                    {"$eq": ["$user_id", user_id]},
                ]}}},
                {"$sort": {"attempted_at": -1}},
                {"$limit": 1},
            ],
            "as": "latest_attempt",
        }},
        {"$addFields": {
            "last_attempt": {"$arrayElemAt": ["$latest_attempt", 0]},
        }},
        {"$lookup": {
            "from": "question_attempts",
            "let": {"qid": "$question_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$question_id", "$$qid"]},
                    {"$eq": ["$user_id", user_id]},
                ]}}},
                {"$group": {
                    "_id": "$question_id",
                    "count": {"$sum": 1},
                    "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                }},
            ],
            "as": "attempt_stats",
        }},
        {"$addFields": {
            "stats": {"$arrayElemAt": ["$attempt_stats", 0]},
        }},
        {"$lookup": {
            "from": "question_flags",
            "localField": "question_id",
            "foreignField": "question_id",
            "as": "flag_docs",
        }},
        {"$addFields": {
            "flags": {
                "$map": {
                    "input": {
                        "$filter": {
                            "input": "$flag_docs",
                            "as": "f",
                            "cond": {"$eq": ["$$f.user_id", user_id]},
                        }
                    },
                    "as": "f",
                    "in": "$$f.flag_type",
                }
            }
        }},
        {"$lookup": {
            "from": "subjects",
            "localField": "subject_id",
            "foreignField": "subject_id",
            "as": "subj",
        }},
        {"$lookup": {
            "from": "topics",
            "localField": "topic_id",
            "foreignField": "topic_id",
            "as": "top",
        }},
        {"$addFields": {
            "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
            "topic_name": {"$arrayElemAt": ["$top.name", 0]},
            "user_progress": {
                "count": {"$ifNull": ["$stats.count", 0]},
                "correct": {"$ifNull": ["$stats.correct", 0]},
                "last_correct": {"$ifNull": ["$last_attempt.is_correct", None]},
            },
        }},
    ]

    if attempted == "true":
        if result == "correct":
            pipeline.append({"$match": {"last_attempt.is_correct": True}})
        elif result == "incorrect":
            pipeline.append({"$match": {"last_attempt.is_correct": False}})
        else:
            pipeline.append({"$match": {"last_attempt": {"$ne": None}}})
    elif attempted == "false":
        pipeline.append({"$match": {"last_attempt": None}})

    if flag in ("review", "important"):
        pipeline.append({"$match": {"flags": flag}})

    pipeline.extend([
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "latest_attempt": 0,
            "attempt_stats": 0,
            "flag_docs": 0,
            "subj": 0,
            "top": 0,
            "stats": 0,
            "last_attempt": 0,
        }},
    ])

    return pipeline


def build_question_count_pipeline(
    user_id: str,
    subject_id: Optional[str],
    topic_id: Optional[str],
    question_type: Optional[str],
    attempted: Optional[str],
    result: Optional[str],
    flag: Optional[str],
) -> list:
    pipeline = build_question_list_pipeline(
        user_id, subject_id, topic_id, question_type,
        attempted, result, flag, skip=0, limit=1,
    )
    pipeline.append({"$count": "total"})
    return pipeline


def build_pyq_list_pipeline(
    user_id: str,
    subject_id: Optional[str],
    topic_id: Optional[str],
    year: Optional[int],
    attempted: Optional[str],
    result: Optional[str],
    flag: Optional[str],
    skip: int,
    limit: int,
) -> list:
    match_q: Dict[str, Any] = {"user_id": user_id}
    if subject_id:
        match_q["subject_id"] = subject_id
    if topic_id:
        match_q["topic_id"] = topic_id
    if year:
        match_q["year"] = year

    pipeline: List[Dict[str, Any]] = [
        {"$match": match_q},
        {"$lookup": {
            "from": "pyq_attempts",
            "let": {"pid": "$pyq_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$pyq_id", "$$pid"]},
                    {"$eq": ["$user_id", user_id]},
                ]}}},
                {"$sort": {"attempted_at": -1}},
                {"$limit": 1},
            ],
            "as": "latest_attempt",
        }},
        {"$addFields": {
            "last_attempt": {"$arrayElemAt": ["$latest_attempt", 0]},
        }},
        {"$lookup": {
            "from": "pyq_attempts",
            "let": {"pid": "$pyq_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$pyq_id", "$$pid"]},
                    {"$eq": ["$user_id", user_id]},
                ]}}},
                {"$group": {
                    "_id": "$pyq_id",
                    "count": {"$sum": 1},
                    "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                }},
            ],
            "as": "attempt_stats",
        }},
        {"$addFields": {
            "stats": {"$arrayElemAt": ["$attempt_stats", 0]},
        }},
        {"$lookup": {
            "from": "pyq_flags",
            "localField": "pyq_id",
            "foreignField": "pyq_id",
            "as": "flag_docs",
        }},
        {"$addFields": {
            "flags": {
                "$map": {
                    "input": {
                        "$filter": {
                            "input": "$flag_docs",
                            "as": "f",
                            "cond": {"$eq": ["$$f.user_id", user_id]},
                        }
                    },
                    "as": "f",
                    "in": "$$f.flag_type",
                }
            }
        }},
        {"$lookup": {
            "from": "subjects",
            "localField": "subject_id",
            "foreignField": "subject_id",
            "as": "subj",
        }},
        {"$lookup": {
            "from": "topics",
            "localField": "topic_id",
            "foreignField": "topic_id",
            "as": "top",
        }},
        {"$addFields": {
            "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
            "topic_name": {"$arrayElemAt": ["$top.name", 0]},
            "user_progress": {
                "count": {"$ifNull": ["$stats.count", 0]},
                "correct": {"$ifNull": ["$stats.correct", 0]},
                "last_correct": {"$ifNull": ["$last_attempt.is_correct", None]},
            },
        }},
    ]

    if attempted == "true":
        if result == "correct":
            pipeline.append({"$match": {"last_attempt.is_correct": True}})
        elif result == "incorrect":
            pipeline.append({"$match": {"last_attempt.is_correct": False}})
        else:
            pipeline.append({"$match": {"last_attempt": {"$ne": None}}})
    elif attempted == "false":
        pipeline.append({"$match": {"last_attempt": None}})

    if flag in ("review", "important"):
        pipeline.append({"$match": {"flags": flag}})

    pipeline.extend([
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "latest_attempt": 0,
            "attempt_stats": 0,
            "flag_docs": 0,
            "subj": 0,
            "top": 0,
            "stats": 0,
            "last_attempt": 0,
        }},
    ])

    return pipeline


def build_pyq_count_pipeline(
    user_id: str,
    subject_id: Optional[str],
    topic_id: Optional[str],
    year: Optional[int],
    attempted: Optional[str],
    result: Optional[str],
    flag: Optional[str],
) -> list:
    pipeline = build_pyq_list_pipeline(
        user_id, subject_id, topic_id, year,
        attempted, result, flag, skip=0, limit=1,
    )
    pipeline.append({"$count": "total"})
    return pipeline


class QuestionService:
    def __init__(self, repo: QuestionRepository):
        self._repo = repo

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
        data_pipeline = build_question_list_pipeline(
            user_id, subject_id, topic_id, question_type,
            attempted, result, flag, skip, limit,
        )
        count_pipeline = build_question_count_pipeline(
            user_id, subject_id, topic_id, question_type,
            attempted, result, flag,
        )

        docs = await self._repo.list_with_aggregation(data_pipeline, limit)
        count_res = await self._repo.list_with_aggregation(count_pipeline, 1)
        total = count_res[0]["total"] if count_res else 0
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
    def __init__(self, repo: PYQRepository):
        self._repo = repo

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
        data_pipeline = build_pyq_list_pipeline(
            user_id, subject_id, topic_id, year,
            attempted, result, flag, skip, limit,
        )
        count_pipeline = build_pyq_count_pipeline(
            user_id, subject_id, topic_id, year,
            attempted, result, flag,
        )

        docs = await self._repo.list_with_aggregation(data_pipeline, limit)
        count_res = await self._repo.list_with_aggregation(count_pipeline, 1)
        total = count_res[0]["total"] if count_res else 0
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
        q: Dict[str, Any] = {"user_id": user_id}
        if subject_id:
            q["subject_id"] = subject_id
        if topic_id:
            q["topic_id"] = topic_id
        if mistake_type:
            q["mistake_type"] = mistake_type

        pipeline = [
            {"$match": q},
            {"$sort": {"created_at": -1}},
            {"$limit": 500},
            {"$lookup": {
                "from": "questions",
                "localField": "question_id",
                "foreignField": "question_id",
                "as": "q_detail",
            }},
            {"$addFields": {
                "question": {"$arrayElemAt": ["$q_detail", 0]},
            }},
            {"$project": {
                "_id": 0,
                "q_detail": 0,
                "question._id": 0,
            }},
        ]
        return await self._repo.list_with_aggregation(pipeline)

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
