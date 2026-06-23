from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shared import db, err, get_current_user, ok, new_id, iso, now_utc

router = APIRouter()


class AttemptIn(BaseModel):
    selected_answer: Any
    time_taken: int = 0


class NotesIn(BaseModel):
    note_content: str


class QuestionIn(BaseModel):
    subject_id: str
    topic_id: str
    question_type: str  # MCQ | MSQ | NAT
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: Any
    solution: str
    difficulty: str = "Medium"
    source: str = "User"
    year: Optional[int] = None


class QuestionPatch(BaseModel):
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Any = None
    solution: Optional[str] = None
    difficulty: Optional[str] = None
    source: Optional[str] = None
    year: Optional[int] = None
    gate_set: Optional[str] = None
    gate_qnum: Optional[str] = None


class PYQIn(QuestionIn):
    year: int
    gate_set: Optional[str] = None
    gate_qnum: Optional[str] = None


VALID_FLAG_TYPES = {"review", "important"}


class FlagIn(BaseModel):
    flag_type: str  # "review" | "important"


class MistakeIn(BaseModel):
    question_id: str
    mistake_type: str
    note: Optional[str] = ""


def _is_correct(qtype: str, correct: Any, selected: Any) -> bool:
    if qtype == "MCQ":
        return str(selected) == str(correct)
    if qtype == "MSQ":
        return sorted([str(x) for x in (selected or [])]) == sorted([str(x) for x in (correct or [])])
    if qtype == "NAT":
        try:
            return abs(float(selected) - float(correct)) < 1e-3
        except Exception:
            return False
    return False


async def get_admin_user(user=Depends(get_current_user)):
    if not user.get("is_admin"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/questions")
async def list_questions(
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    attempted: Optional[str] = None,
    result: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user=Depends(get_current_user),
):
    uid = user["user_id"]
    
    # 1. Base Match
    match_q: Dict[str, Any] = {"user_id": uid}
    if subject_id: match_q["subject_id"] = subject_id
    if topic_id: match_q["topic_id"] = topic_id
    if difficulty: match_q["difficulty"] = difficulty
    if question_type: match_q["question_type"] = question_type

    # 2. Build Pipeline
    pipeline: List[Dict[str, Any]] = [
        {"$match": match_q},
        # Join with latest attempt
        {"$lookup": {
            "from": "question_attempts",
            "let": {"qid": "$question_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$question_id", "$$qid"]},
                    {"$eq": ["$user_id", uid]}
                ]}}},
                {"$sort": {"attempted_at": -1}},
                {"$limit": 1}
            ],
            "as": "latest_attempt"
        }},
        {"$addFields": {
            "last_attempt": {"$arrayElemAt": ["$latest_attempt", 0]}
        }},
        # Join with all attempts for summary
        {"$lookup": {
            "from": "question_attempts",
            "let": {"qid": "$question_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$question_id", "$$qid"]},
                    {"$eq": ["$user_id", uid]}
                ]}}},
                {"$group": {
                    "_id": "$question_id",
                    "count": {"$sum": 1},
                    "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}
                }}
            ],
            "as": "attempt_stats"
        }},
        {"$addFields": {
            "stats": {"$arrayElemAt": ["$attempt_stats", 0]}
        }},
        # Join with flags
        {"$lookup": {
            "from": "question_flags",
            "localField": "question_id",
            "foreignField": "question_id",
            "as": "flag_docs"
        }},
        {"$addFields": {
            "flags": {
                "$map": {
                    "input": {"$filter": {
                        "input": "$flag_docs",
                        "as": "f",
                        "cond": {"$eq": ["$$f.user_id", uid]}
                    }},
                    "as": "f",
                    "in": "$$f.flag_type"
                }
            }
        }},
        # Join with subject/topic names
        {"$lookup": {
            "from": "subjects",
            "localField": "subject_id",
            "foreignField": "subject_id",
            "as": "subj"
        }},
        {"$lookup": {
            "from": "topics",
            "localField": "topic_id",
            "foreignField": "topic_id",
            "as": "top"
        }},
        {"$addFields": {
            "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
            "topic_name": {"$arrayElemAt": ["$top.name", 0]},
            "user_progress": {
                "count": {"$ifNull": ["$stats.count", 0]},
                "correct": {"$ifNull": ["$stats.correct", 0]},
                "last_correct": {"$ifNull": ["$last_attempt.is_correct", None]}
            }
        }}
    ]

    # 3. Apply Filters that depend on joined data
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

    # 4. Count total
    count_pipeline = pipeline + [{"$count": "total"}]
    count_res = await db.questions.aggregate(count_pipeline).to_list(1)
    total = count_res[0]["total"] if count_res else 0

    # 5. Skip/Limit/Project
    pipeline.extend([
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "latest_attempt": 0, "attempt_stats": 0, "flag_docs": 0, 
            "subj": 0, "top": 0, "stats": 0, "last_attempt": 0
        }}
    ])

    docs = await db.questions.aggregate(pipeline).to_list(limit)
    return ok({"items": docs, "total": total})


@router.get("/questions/{question_id}")
async def get_question(question_id: str, user=Depends(get_current_user)):
    q = await db.questions.find_one({"question_id": question_id, "user_id": user["user_id"]}, {"_id": 0})
    if not q:
        return err("not_found", "Question not found", 404)
    flags = await db.question_flags.find({"user_id": user["user_id"], "question_id": question_id}, {"_id": 0, "flag_type": 1}).to_list(10)
    q["flags"] = [f["flag_type"] for f in flags]
    return ok(q)


@router.post("/questions/{question_id}/attempt")
async def attempt_question(question_id: str, body: AttemptIn, user=Depends(get_current_user)):
    q = await db.questions.find_one({"question_id": question_id, "user_id": user["user_id"]}, {"_id": 0})
    if not q:
        return err("not_found", "Question not found", 404)
    correct = _is_correct(q["question_type"], q["correct_answer"], body.selected_answer)
    attempt = {
        "attempt_id": new_id("att"),
        "user_id": user["user_id"],
        "question_id": question_id,
        "selected_answer": body.selected_answer,
        "is_correct": correct,
        "time_taken": body.time_taken,
        "attempted_at": iso(now_utc()),
    }
    await db.question_attempts.insert_one(dict(attempt))
    attempt.pop("_id", None)
    return ok({"attempt": attempt, "correct_answer": q["correct_answer"], "solution": q["solution"]})


@router.get("/questions/{question_id}/attempts")
async def question_attempts(question_id: str, user=Depends(get_current_user)):
    docs = await db.question_attempts.find({"user_id": user["user_id"], "question_id": question_id}, {"_id": 0}).sort("attempted_at", -1).to_list(200)
    return ok(docs)


@router.get("/questions/{question_id}/notes")
async def get_question_notes(question_id: str, user=Depends(get_current_user)):
    n = await db.question_notes.find_one({"user_id": user["user_id"], "question_id": question_id}, {"_id": 0})
    return ok(n or {"note_content": "", "question_id": question_id})


@router.post("/questions/{question_id}/notes")
async def save_question_notes(question_id: str, body: NotesIn, user=Depends(get_current_user)):
    await db.question_notes.update_one(
        {"user_id": user["user_id"], "question_id": question_id},
        {"$set": {"note_content": body.note_content, "updated_at": iso(now_utc())},
         "$setOnInsert": {"note_id": new_id("note"), "user_id": user["user_id"],
                          "question_id": question_id, "created_at": iso(now_utc())}},
        upsert=True,
    )
    return ok({"saved": True})


@router.post("/questions")
async def create_question(body: QuestionIn, user=Depends(get_current_user)):
    doc = {
        "question_id": new_id("q"),
        "user_id": user["user_id"],
        **body.model_dump(),
        "created_at": iso(now_utc()),
    }
    await db.questions.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)


@router.put("/questions/{question_id}")
async def update_question(question_id: str, body: QuestionPatch, user=Depends(get_current_user)):
    upd = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == "correct_answer"}
    if not upd:
        return err("nothing_to_update", "No fields supplied", 400)
    upd["updated_at"] = iso(now_utc())
    r = await db.questions.update_one(
        {"question_id": question_id, "user_id": user["user_id"]}, {"$set": upd}
    )
    if r.matched_count == 0:
        return err("not_found", "Question not found", 404)
    doc = await db.questions.find_one(
        {"question_id": question_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    return ok(doc)


@router.delete("/questions/{question_id}")
async def delete_question(question_id: str, user=Depends(get_current_user)):
    r = await db.questions.delete_one(
        {"question_id": question_id, "user_id": user["user_id"]}
    )
    if r.deleted_count == 0:
        return err("not_found", "Question not found", 404)
    await db.question_attempts.delete_many({"user_id": user["user_id"], "question_id": question_id})
    await db.question_notes.delete_many({"user_id": user["user_id"], "question_id": question_id})
    await db.question_flags.delete_many({"user_id": user["user_id"], "question_id": question_id})
    await db.mistakes.delete_many({"user_id": user["user_id"], "question_id": question_id})
    return ok({"deleted": 1})


@router.get("/pyqs")
async def list_pyqs(
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    year: Optional[int] = None,
    attempted: Optional[str] = None,
    result: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user=Depends(get_current_user),
):
    uid = user["user_id"]
    match_q: Dict[str, Any] = {"user_id": uid}
    if subject_id: match_q["subject_id"] = subject_id
    if topic_id: match_q["topic_id"] = topic_id
    if year: match_q["year"] = year

    pipeline: List[Dict[str, Any]] = [
        {"$match": match_q},
        {"$lookup": {
            "from": "pyq_attempts",
            "let": {"pid": "$pyq_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$pyq_id", "$$pid"]},
                    {"$eq": ["$user_id", uid]}
                ]}}},
                {"$sort": {"attempted_at": -1}},
                {"$limit": 1}
            ],
            "as": "latest_attempt"
        }},
        {"$addFields": {
            "last_attempt": {"$arrayElemAt": ["$latest_attempt", 0]}
        }},
        {"$lookup": {
            "from": "pyq_attempts",
            "let": {"pid": "$pyq_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$pyq_id", "$$pid"]},
                    {"$eq": ["$user_id", uid]}
                ]}}},
                {"$group": {
                    "_id": "$pyq_id",
                    "count": {"$sum": 1},
                    "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}
                }}
            ],
            "as": "attempt_stats"
        }},
        {"$addFields": {
            "stats": {"$arrayElemAt": ["$attempt_stats", 0]}
        }},
        {"$lookup": {
            "from": "pyq_flags",
            "localField": "pyq_id",
            "foreignField": "pyq_id",
            "as": "flag_docs"
        }},
        {"$addFields": {
            "flags": {
                "$map": {
                    "input": {"$filter": {
                        "input": "$flag_docs",
                        "as": "f",
                        "cond": {"$eq": ["$$f.user_id", uid]}
                    }},
                    "as": "f",
                    "in": "$$f.flag_type"
                }
            }
        }},
        {"$lookup": {
            "from": "subjects",
            "localField": "subject_id",
            "foreignField": "subject_id",
            "as": "subj"
        }},
        {"$lookup": {
            "from": "topics",
            "localField": "topic_id",
            "foreignField": "topic_id",
            "as": "top"
        }},
        {"$addFields": {
            "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
            "topic_name": {"$arrayElemAt": ["$top.name", 0]},
            "user_progress": {
                "count": {"$ifNull": ["$stats.count", 0]},
                "correct": {"$ifNull": ["$stats.correct", 0]},
                "last_correct": {"$ifNull": ["$last_attempt.is_correct", None]}
            }
        }}
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

    count_pipeline = pipeline + [{"$count": "total"}]
    count_res = await db.pyqs.aggregate(count_pipeline).to_list(1)
    total = count_res[0]["total"] if count_res else 0

    pipeline.extend([
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "latest_attempt": 0, "attempt_stats": 0, "flag_docs": 0, 
            "subj": 0, "top": 0, "stats": 0, "last_attempt": 0
        }}
    ])

    docs = await db.pyqs.aggregate(pipeline).to_list(limit)
    return ok({"items": docs, "total": total})


@router.post("/pyqs")
async def create_pyq(body: PYQIn, user=Depends(get_current_user)):
    doc = {
        "pyq_id": new_id("pyq"),
        "user_id": user["user_id"],
        **body.model_dump(),
        "created_at": iso(now_utc()),
    }
    await db.pyqs.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)


@router.put("/pyqs/{pyq_id}")
async def update_pyq(pyq_id: str, body: QuestionPatch, user=Depends(get_current_user)):
    upd = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == "correct_answer"}
    if not upd:
        return err("nothing_to_update", "No fields supplied", 400)
    upd["updated_at"] = iso(now_utc())
    r = await db.pyqs.update_one(
        {"pyq_id": pyq_id, "user_id": user["user_id"]}, {"$set": upd}
    )
    if r.matched_count == 0:
        return err("not_found", "PYQ not found", 404)
    doc = await db.pyqs.find_one(
        {"pyq_id": pyq_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    return ok(doc)


@router.delete("/pyqs/{pyq_id}")
async def delete_pyq(pyq_id: str, user=Depends(get_current_user)):
    r = await db.pyqs.delete_one(
        {"pyq_id": pyq_id, "user_id": user["user_id"]}
    )
    if r.deleted_count == 0:
        return err("not_found", "PYQ not found", 404)
    await db.pyq_attempts.delete_many({"user_id": user["user_id"], "pyq_id": pyq_id})
    await db.pyq_flags.delete_many({"user_id": user["user_id"], "pyq_id": pyq_id})
    return ok({"deleted": 1})


@router.post("/questions/{question_id}/flag")
async def flag_question(question_id: str, body: FlagIn, user=Depends(get_current_user)):
    if body.flag_type not in VALID_FLAG_TYPES:
        return err("invalid_flag", f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}", 400)
    q = await db.questions.find_one(
        {"question_id": question_id, "user_id": user["user_id"]}, {"_id": 0, "question_id": 1}
    )
    if not q:
        return err("not_found", "Question not found", 404)
    await db.question_flags.update_one(
        {"user_id": user["user_id"], "question_id": question_id, "flag_type": body.flag_type},
        {"$set": {"updated_at": iso(now_utc())},
         "$setOnInsert": {
            "user_id": user["user_id"], "question_id": question_id,
            "flag_type": body.flag_type, "created_at": iso(now_utc()),
         }},
        upsert=True,
    )
    flags = await db.question_flags.find(
        {"user_id": user["user_id"], "question_id": question_id}, {"_id": 0, "flag_type": 1}
    ).to_list(10)
    return ok({"flags": [f["flag_type"] for f in flags]})


@router.delete("/questions/{question_id}/flag/{flag_type}")
async def unflag_question(question_id: str, flag_type: str, user=Depends(get_current_user)):
    if flag_type not in VALID_FLAG_TYPES:
        return err("invalid_flag", f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}", 400)
    await db.question_flags.delete_one(
        {"user_id": user["user_id"], "question_id": question_id, "flag_type": flag_type}
    )
    flags = await db.question_flags.find(
        {"user_id": user["user_id"], "question_id": question_id}, {"_id": 0, "flag_type": 1}
    ).to_list(10)
    return ok({"flags": [f["flag_type"] for f in flags]})


@router.post("/pyqs/{pyq_id}/flag")
async def flag_pyq(pyq_id: str, body: FlagIn, user=Depends(get_current_user)):
    if body.flag_type not in VALID_FLAG_TYPES:
        return err("invalid_flag", f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}", 400)
    p = await db.pyqs.find_one(
        {"pyq_id": pyq_id, "user_id": user["user_id"]}, {"_id": 0, "pyq_id": 1}
    )
    if not p:
        return err("not_found", "PYQ not found", 404)
    await db.pyq_flags.update_one(
        {"user_id": user["user_id"], "pyq_id": pyq_id, "flag_type": body.flag_type},
        {"$set": {"updated_at": iso(now_utc())},
         "$setOnInsert": {
            "user_id": user["user_id"], "pyq_id": pyq_id,
            "flag_type": body.flag_type, "created_at": iso(now_utc()),
         }},
        upsert=True,
    )
    flags = await db.pyq_flags.find(
        {"user_id": user["user_id"], "pyq_id": pyq_id}, {"_id": 0, "flag_type": 1}
    ).to_list(10)
    return ok({"flags": [f["flag_type"] for f in flags]})


@router.delete("/pyqs/{pyq_id}/flag/{flag_type}")
async def unflag_pyq(pyq_id: str, flag_type: str, user=Depends(get_current_user)):
    if flag_type not in VALID_FLAG_TYPES:
        return err("invalid_flag", f"flag_type must be one of {sorted(VALID_FLAG_TYPES)}", 400)
    await db.pyq_flags.delete_one(
        {"user_id": user["user_id"], "pyq_id": pyq_id, "flag_type": flag_type}
    )
    flags = await db.pyq_flags.find(
        {"user_id": user["user_id"], "pyq_id": pyq_id}, {"_id": 0, "flag_type": 1}
    ).to_list(10)
    return ok({"flags": [f["flag_type"] for f in flags]})


@router.post("/admin/questions")
async def admin_create_question(body: QuestionIn, user=Depends(get_admin_user)):
    return await create_question(body, user)


@router.delete("/admin/questions/{question_id}")
async def admin_delete_question(question_id: str, user=Depends(get_admin_user)):
    return await delete_question(question_id, user)


@router.post("/admin/pyqs")
async def admin_create_pyq(body: PYQIn, user=Depends(get_admin_user)):
    return await create_pyq(body, user)


@router.delete("/admin/pyqs/{pyq_id}")
async def admin_delete_pyq(pyq_id: str, user=Depends(get_admin_user)):
    return await delete_pyq(pyq_id, user)


@router.get("/admin/users")
async def admin_users(user=Depends(get_admin_user)):
    docs = await db.users.find({}, {"_id": 0}).to_list(10000)
    return ok(docs)


@router.post("/pyqs/{pyq_id}/attempt")
async def attempt_pyq(pyq_id: str, body: AttemptIn, user=Depends(get_current_user)):
    p = await db.pyqs.find_one({"pyq_id": pyq_id, "user_id": user["user_id"]}, {"_id": 0})
    if not p:
        return err("not_found", "PYQ not found", 404)
    correct = _is_correct(p["question_type"], p["correct_answer"], body.selected_answer)
    attempt = {
        "attempt_id": new_id("att"),
        "user_id": user["user_id"],
        "pyq_id": pyq_id,
        "selected_answer": body.selected_answer,
        "is_correct": correct,
        "time_taken": body.time_taken,
        "attempted_at": iso(now_utc()),
    }
    await db.pyq_attempts.insert_one(dict(attempt))
    attempt.pop("_id", None)
    return ok({"attempt": attempt, "correct_answer": p["correct_answer"], "solution": p["solution"]})


@router.get("/pyqs/{pyq_id}/attempts")
async def pyq_attempts_list(pyq_id: str, user=Depends(get_current_user)):
    docs = await db.pyq_attempts.find({"user_id": user["user_id"], "pyq_id": pyq_id}, {"_id": 0}).sort("attempted_at", -1).to_list(200)
    return ok(docs)



@router.get("/mistakes")
async def list_mistakes(
    subject_id: Optional[str] = None, topic_id: Optional[str] = None,
    mistake_type: Optional[str] = None, user=Depends(get_current_user),
):
    uid = user["user_id"]
    q: Dict[str, Any] = {"user_id": uid}
    if subject_id: q["subject_id"] = subject_id
    if topic_id: q["topic_id"] = topic_id
    if mistake_type: q["mistake_type"] = mistake_type
    
    pipeline = [
        {"$match": q},
        {"$sort": {"created_at": -1}},
        {"$limit": 500},
        {"$lookup": {
            "from": "questions",
            "localField": "question_id",
            "foreignField": "question_id",
            "as": "q_detail"
        }},
        {"$addFields": {
            "question": {"$arrayElemAt": ["$q_detail", 0]}
        }},
        {"$project": {
            "_id": 0, 
            "q_detail": 0,
            "question._id": 0  # CRITICAL: Project out ObjectId from joined doc
        }}
    ]
    docs = await db.mistakes.aggregate(pipeline).to_list(500)
    return ok(docs)


@router.post("/mistakes")
async def create_mistake(body: MistakeIn, user=Depends(get_current_user)):
    q = await db.questions.find_one({"question_id": body.question_id}, {"_id": 0})
    if not q:
        return err("not_found", "Question not found", 404)
    doc = {
        "mistake_id": new_id("mis"), "user_id": user["user_id"],
        "question_id": body.question_id, "subject_id": q["subject_id"],
        "topic_id": q["topic_id"], "mistake_type": body.mistake_type,
        "note": body.note or "", "created_at": iso(now_utc()),
    }
    await db.mistakes.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)


@router.delete("/mistakes/{mistake_id}")
async def delete_mistake(mistake_id: str, user=Depends(get_current_user)):
    r = await db.mistakes.delete_one({"mistake_id": mistake_id, "user_id": user["user_id"]})
    return ok({"deleted": r.deleted_count})
