from __future__ import annotations

from typing import Any, Dict, List, Optional


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
        {
            "$lookup": {
                "from": "question_attempts",
                "let": {"qid": "$question_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$question_id", "$$qid"]},
                                    {"$eq": ["$user_id", user_id]},
                                ]
                            }
                        }
                    },
                    {"$sort": {"attempted_at": -1}},
                    {"$limit": 1},
                ],
                "as": "latest_attempt",
            }
        },
        {"$addFields": {"last_attempt": {"$arrayElemAt": ["$latest_attempt", 0]}}},
        {
            "$lookup": {
                "from": "question_attempts",
                "let": {"qid": "$question_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$question_id", "$$qid"]},
                                    {"$eq": ["$user_id", user_id]},
                                ]
                            }
                        }
                    },
                    {
                        "$group": {
                            "_id": "$question_id",
                            "count": {"$sum": 1},
                            "correct": {
                                "$sum": {"$cond": ["$is_correct", 1, 0]}
                            },
                        }
                    },
                ],
                "as": "attempt_stats",
            }
        },
        {"$addFields": {"stats": {"$arrayElemAt": ["$attempt_stats", 0]}}},
        {
            "$lookup": {
                "from": "question_flags",
                "localField": "question_id",
                "foreignField": "question_id",
                "as": "flag_docs",
            }
        },
        {
            "$addFields": {
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
            }
        },
        {
            "$lookup": {
                "from": "subjects",
                "localField": "subject_id",
                "foreignField": "subject_id",
                "as": "subj",
            }
        },
        {
            "$lookup": {
                "from": "topics",
                "localField": "topic_id",
                "foreignField": "topic_id",
                "as": "top",
            }
        },
        {
            "$addFields": {
                "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
                "topic_name": {"$arrayElemAt": ["$top.name", 0]},
                "user_progress": {
                    "count": {"$ifNull": ["$stats.count", 0]},
                    "correct": {"$ifNull": ["$stats.correct", 0]},
                    "last_correct": {
                        "$ifNull": ["$last_attempt.is_correct", None]
                    },
                },
            }
        },
    ]

    _append_attempt_and_flag_filters(pipeline, attempted, result, flag)
    _append_list_tail(pipeline, skip, limit, "question_id")
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
    match_q: Dict[str, Any] = {"user_id": user_id}
    if subject_id:
        match_q["subject_id"] = subject_id
    if topic_id:
        match_q["topic_id"] = topic_id
    if question_type:
        match_q["question_type"] = question_type

    needs_lookup = bool(attempted) or flag in ("review", "important")
    if not needs_lookup:
        return [{"$match": match_q}, {"$count": "total"}]

    pipeline = build_question_list_pipeline(
        user_id,
        subject_id,
        topic_id,
        question_type,
        attempted,
        result,
        flag,
        skip=0,
        limit=1,
    )
    _remove_list_tail(pipeline)
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
        {
            "$lookup": {
                "from": "pyq_attempts",
                "let": {"pid": "$pyq_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$pyq_id", "$$pid"]},
                                    {"$eq": ["$user_id", user_id]},
                                ]
                            }
                        }
                    },
                    {"$sort": {"attempted_at": -1}},
                    {"$limit": 1},
                ],
                "as": "latest_attempt",
            }
        },
        {"$addFields": {"last_attempt": {"$arrayElemAt": ["$latest_attempt", 0]}}},
        {
            "$lookup": {
                "from": "pyq_attempts",
                "let": {"pid": "$pyq_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$pyq_id", "$$pid"]},
                                    {"$eq": ["$user_id", user_id]},
                                ]
                            }
                        }
                    },
                    {
                        "$group": {
                            "_id": "$pyq_id",
                            "count": {"$sum": 1},
                            "correct": {
                                "$sum": {"$cond": ["$is_correct", 1, 0]}
                            },
                        }
                    },
                ],
                "as": "attempt_stats",
            }
        },
        {"$addFields": {"stats": {"$arrayElemAt": ["$attempt_stats", 0]}}},
        {
            "$lookup": {
                "from": "pyq_flags",
                "localField": "pyq_id",
                "foreignField": "pyq_id",
                "as": "flag_docs",
            }
        },
        {
            "$addFields": {
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
            }
        },
        {
            "$lookup": {
                "from": "subjects",
                "localField": "subject_id",
                "foreignField": "subject_id",
                "as": "subj",
            }
        },
        {
            "$lookup": {
                "from": "topics",
                "localField": "topic_id",
                "foreignField": "topic_id",
                "as": "top",
            }
        },
        {
            "$addFields": {
                "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
                "topic_name": {"$arrayElemAt": ["$top.name", 0]},
                "user_progress": {
                    "count": {"$ifNull": ["$stats.count", 0]},
                    "correct": {"$ifNull": ["$stats.correct", 0]},
                    "last_correct": {
                        "$ifNull": ["$last_attempt.is_correct", None]
                    },
                },
            }
        },
    ]

    _append_attempt_and_flag_filters(pipeline, attempted, result, flag)
    _append_list_tail(pipeline, skip, limit, "pyq_id")
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
    match_q: Dict[str, Any] = {"user_id": user_id}
    if subject_id:
        match_q["subject_id"] = subject_id
    if topic_id:
        match_q["topic_id"] = topic_id
    if year:
        match_q["year"] = year

    needs_lookup = bool(attempted) or flag in ("review", "important")
    if not needs_lookup:
        return [{"$match": match_q}, {"$count": "total"}]

    pipeline = build_pyq_list_pipeline(
        user_id,
        subject_id,
        topic_id,
        year,
        attempted,
        result,
        flag,
        skip=0,
        limit=1,
    )
    _remove_list_tail(pipeline)
    pipeline.append({"$count": "total"})
    return pipeline


def build_mistake_list_pipeline(
    user_id: str,
    subject_id: Optional[str],
    topic_id: Optional[str],
    mistake_type: Optional[str],
) -> list:
    match_q: Dict[str, Any] = {"user_id": user_id}
    if subject_id:
        match_q["subject_id"] = subject_id
    if topic_id:
        match_q["topic_id"] = topic_id
    if mistake_type:
        match_q["mistake_type"] = mistake_type

    return [
        {"$match": match_q},
        {"$sort": {"created_at": -1}},
        {"$limit": 500},
        {
            "$lookup": {
                "from": "questions",
                "localField": "question_id",
                "foreignField": "question_id",
                "as": "q_detail",
            }
        },
        {
            "$addFields": {
                "question": {"$arrayElemAt": ["$q_detail", 0]},
            }
        },
        {
            "$project": {
                "_id": 0,
                "q_detail": 0,
                "question._id": 0,
            }
        },
    ]


def _append_attempt_and_flag_filters(
    pipeline: list,
    attempted: Optional[str],
    result: Optional[str],
    flag: Optional[str],
) -> None:
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


def _append_list_tail(pipeline: list, skip: int, limit: int, stable_id_field: str) -> None:
    pipeline.extend(
        [
            {"$sort": {"created_at": -1, stable_id_field: 1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "latest_attempt": 0,
                    "attempt_stats": 0,
                    "flag_docs": 0,
                    "subj": 0,
                    "top": 0,
                    "stats": 0,
                    "last_attempt": 0,
                }
            },
        ]
    )


def _remove_list_tail(pipeline: list) -> None:
    del pipeline[-4:]
