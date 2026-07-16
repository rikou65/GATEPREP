from __future__ import annotations

from typing import Any, Dict


def subject_total_pipeline(user_id: str) -> list[Dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}},
    ]


def topic_total_pipeline(user_id: str, subject_id: str) -> list[Dict[str, Any]]:
    return [
        {"$match": {"subject_id": subject_id, "user_id": user_id}},
        {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}},
    ]


def question_ids_by_topic_pipeline(subject_id: str) -> list[Dict[str, Any]]:
    return [
        {"$match": {"subject_id": subject_id}},
        {"$project": {"question_id": 1, "topic_id": 1}},
    ]


def question_ids_for_topic_pipeline(topic_id: str) -> list[Dict[str, Any]]:
    return [
        {"$match": {"topic_id": topic_id}},
        {"$project": {"question_id": 1}},
    ]


def notes_by_question_pipeline(
    user_id: str, question_ids: list[str]
) -> list[Dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id, "question_id": {"$in": question_ids}}},
        {"$group": {"_id": "$question_id"}},
    ]


def mistakes_by_topic_pipeline(
    user_id: str, subject_id: str
) -> list[Dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id, "subject_id": subject_id}},
        {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}},
    ]


def recent_question_activity_pipeline(user_id: str) -> list[Dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id}},
        {"$sort": {"attempted_at": -1}},
        {"$limit": 10},
        {
            "$lookup": {
                "from": "questions",
                "localField": "question_id",
                "foreignField": "question_id",
                "as": "q",
            }
        },
        {"$unwind": {"path": "$q", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "subjects",
                "localField": "q.subject_id",
                "foreignField": "subject_id",
                "as": "subj",
            }
        },
        {
            "$lookup": {
                "from": "topics",
                "localField": "q.topic_id",
                "foreignField": "topic_id",
                "as": "top",
            }
        },
        {
            "$project": {
                "_id": 0,
                "attempt_id": 1,
                "question_id": 1,
                "is_correct": 1,
                "time_taken": 1,
                "attempted_at": 1,
                "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
                "topic_name": {"$arrayElemAt": ["$top.name", 0]},
                "question_type": "$q.question_type",
            }
        },
    ]


def recent_pyq_activity_pipeline(user_id: str) -> list[Dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id}},
        {"$sort": {"attempted_at": -1}},
        {"$limit": 10},
        {
            "$lookup": {
                "from": "pyqs",
                "localField": "pyq_id",
                "foreignField": "pyq_id",
                "as": "q",
            }
        },
        {"$unwind": {"path": "$q", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "subjects",
                "localField": "q.subject_id",
                "foreignField": "subject_id",
                "as": "subj",
            }
        },
        {
            "$lookup": {
                "from": "topics",
                "localField": "q.topic_id",
                "foreignField": "topic_id",
                "as": "top",
            }
        },
        {
            "$project": {
                "_id": 0,
                "attempt_id": 1,
                "pyq_id": 1,
                "is_correct": 1,
                "time_taken": 1,
                "attempted_at": 1,
                "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
                "topic_name": {"$arrayElemAt": ["$top.name", 0]},
                "question_type": "$q.question_type",
                "year": "$q.year",
            }
        },
    ]


def single_topic_stats_pipeline(
    user_id: str, topic_id: str, id_field: str, item_collection: str
) -> list[Dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id}},
        {"$sort": {"attempted_at": -1}},
        {
            "$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }
        },
        {
            "$lookup": {
                "from": item_collection,
                "localField": "_id",
                "foreignField": id_field,
                "as": "i",
            }
        },
        {"$unwind": "$i"},
        {"$match": {"i.topic_id": topic_id}},
        {
            "$group": {
                "_id": None,
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }
        },
    ]
