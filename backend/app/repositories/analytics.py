from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from app.repositories.analytics_queries import (
    mistakes_by_topic_pipeline,
    notes_by_question_pipeline,
    question_ids_by_topic_pipeline,
    question_ids_for_topic_pipeline,
    recent_pyq_activity_pipeline,
    recent_question_activity_pipeline,
    single_topic_stats_pipeline,
    subject_total_pipeline,
    topic_total_pipeline,
)


class AnalyticsRepository:
    def __init__(self, db):
        self._db = db

    async def count_user_dashboard_items(self, user_id: str) -> Dict[str, int]:
        playlists, videos_done, mistakes, resources = await asyncio.gather(
            self._db.playlists.count_documents({"user_id": user_id}),
            self._db.video_progress.count_documents(
                {"user_id": user_id, "completed": True}
            ),
            self._db.mistakes.count_documents({"user_id": user_id}),
            self._db.resources.count_documents({"user_id": user_id}),
        )
        return {
            "playlists": playlists,
            "videos_done": videos_done,
            "mistakes": mistakes,
            "resources": resources,
        }

    async def get_latest_qbank_attempt_stats(self, user_id: str) -> Dict[str, Any]:
        return await self._get_latest_attempt_stats(
            user_id, "question_attempts", "question_id"
        )

    async def get_latest_pyq_attempt_stats(self, user_id: str) -> Dict[str, Any]:
        return await self._get_latest_attempt_stats(user_id, "pyq_attempts", "pyq_id")

    async def get_qbank_subject_breakdown(
        self, user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        return await self._get_subject_breakdown(
            user_id, "question_attempts", "questions", "question_id"
        )

    async def get_pyq_subject_breakdown(
        self, user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        return await self._get_subject_breakdown(
            user_id, "pyq_attempts", "pyqs", "pyq_id"
        )

    async def get_qbank_topic_breakdown(
        self, user_id: str, subject_id: str
    ) -> Dict[str, Dict[str, Any]]:
        return await self._get_topic_breakdown(
            user_id, "question_attempts", "questions", "question_id", subject_id
        )

    async def get_pyq_topic_breakdown(
        self, user_id: str, subject_id: str
    ) -> Dict[str, Dict[str, Any]]:
        return await self._get_topic_breakdown(
            user_id, "pyq_attempts", "pyqs", "pyq_id", subject_id
        )

    async def list_subjects(self) -> list:
        cursor = self._db.subjects.find(
            {}, {"_id": 0, "subject_id": 1, "name": 1, "order": 1}
        )
        return await cursor.to_list(None)

    async def list_topics_for_subject(self, subject_id: str) -> list:
        cursor = self._db.topics.find(
            {"subject_id": subject_id},
            {"_id": 0, "topic_id": 1, "name": 1, "order": 1},
        )
        return await cursor.to_list(None)

    async def find_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.topics.find_one({"topic_id": topic_id}, {"_id": 0})

    async def get_qbank_subject_totals(self, user_id: str) -> Dict[str, int]:
        return await self._count_by_id("questions", subject_total_pipeline(user_id))

    async def get_pyq_subject_totals(self, user_id: str) -> Dict[str, int]:
        return await self._count_by_id("pyqs", subject_total_pipeline(user_id))

    async def get_qbank_topic_totals(
        self, user_id: str, subject_id: str
    ) -> Dict[str, int]:
        return await self._count_by_id(
            "questions", topic_total_pipeline(user_id, subject_id)
        )

    async def get_pyq_topic_totals(
        self, user_id: str, subject_id: str
    ) -> Dict[str, int]:
        return await self._count_by_id("pyqs", topic_total_pipeline(user_id, subject_id))

    async def get_question_ids_by_topic(
        self, subject_id: str
    ) -> Dict[str, list[str]]:
        rows = await self._db.questions.aggregate(
            question_ids_by_topic_pipeline(subject_id)
        ).to_list(None)
        grouped: Dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["topic_id"], []).append(row["question_id"])
        return grouped

    async def get_question_ids_for_topic(self, topic_id: str) -> list[str]:
        rows = await self._db.questions.aggregate(
            question_ids_for_topic_pipeline(topic_id)
        ).to_list(None)
        return [row["question_id"] for row in rows]

    async def get_noted_question_ids(
        self, user_id: str, question_ids: list[str]
    ) -> set[str]:
        if not question_ids:
            return set()
        rows = await self._db.question_notes.aggregate(
            notes_by_question_pipeline(user_id, question_ids)
        ).to_list(None)
        return {row["_id"] for row in rows}

    async def get_mistake_counts_by_topic(
        self, user_id: str, subject_id: str
    ) -> Dict[str, int]:
        return await self._count_by_id(
            "mistakes", mistakes_by_topic_pipeline(user_id, subject_id)
        )

    async def get_recent_question_activity(self, user_id: str) -> List[Dict[str, Any]]:
        return await self._db.question_attempts.aggregate(
            recent_question_activity_pipeline(user_id)
        ).to_list(None)

    async def get_recent_pyq_activity(self, user_id: str) -> List[Dict[str, Any]]:
        return await self._db.pyq_attempts.aggregate(
            recent_pyq_activity_pipeline(user_id)
        ).to_list(None)

    async def get_qbank_topic_stats(
        self, user_id: str, topic_id: str
    ) -> Dict[str, int]:
        return await self._single_topic_stats(
            "question_attempts", user_id, topic_id, "question_id", "questions"
        )

    async def get_pyq_topic_stats(
        self, user_id: str, topic_id: str
    ) -> Dict[str, int]:
        return await self._single_topic_stats(
            "pyq_attempts", user_id, topic_id, "pyq_id", "pyqs"
        )

    async def count_qbank_for_topic(self, user_id: str, topic_id: str) -> int:
        return await self._db.questions.count_documents(
            {"topic_id": topic_id, "user_id": user_id}
        )

    async def count_pyqs_for_topic(self, user_id: str, topic_id: str) -> int:
        return await self._db.pyqs.count_documents(
            {"topic_id": topic_id, "user_id": user_id}
        )

    async def count_notes_for_questions(
        self, user_id: str, question_ids: list[str]
    ) -> int:
        return await self._db.question_notes.count_documents(
            {"user_id": user_id, "question_id": {"$in": question_ids}}
        )

    async def count_mistakes_for_topic(self, user_id: str, topic_id: str) -> int:
        return await self._db.mistakes.count_documents(
            {"user_id": user_id, "topic_id": topic_id}
        )

    async def _count_by_id(
        self, collection: str, pipeline: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        rows = await self._db[collection].aggregate(pipeline).to_list(None)
        return {row["_id"]: row["count"] for row in rows if row["_id"]}

    async def _single_topic_stats(
        self,
        collection: str,
        user_id: str,
        topic_id: str,
        id_field: str,
        item_collection: str,
    ) -> Dict[str, int]:
        rows = await self._db[collection].aggregate(
            single_topic_stats_pipeline(user_id, topic_id, id_field, item_collection)
        ).to_list(None)
        if not rows:
            return {"solved": 0, "correct": 0}
        return {"solved": rows[0]["solved"], "correct": rows[0]["correct"]}

    async def _get_latest_attempt_stats(
        self, user_id: str, attempt_collection: str, id_field: str
    ) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }},
            {"$group": {
                "_id": None,
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }},
            {"$project": {"_id": 0}},
        ]
        cursor = self._db[attempt_collection].aggregate(pipeline)
        res = await cursor.to_list(1)
        if not res:
            return {"solved": 0, "accuracy": 0.0}
        stats = res[0]
        solved = stats["solved"]
        accuracy = round(stats["correct"] / solved * 100, 1) if solved > 0 else 0.0
        return {"solved": solved, "accuracy": accuracy}

    async def _get_subject_breakdown(
        self, user_id: str, attempt_collection: str, item_collection: str, id_field: str
    ) -> Dict[str, Dict[str, Any]]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }},
            {"$lookup": {
                "from": item_collection,
                "localField": "_id",
                "foreignField": id_field,
                "as": "item",
            }},
            {"$unwind": "$item"},
            {"$group": {
                "_id": "$item.subject_id",
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }},
        ]
        rows = await self._db[attempt_collection].aggregate(pipeline).to_list(None)
        return {r["_id"]: {"solved": r["solved"], "correct": r["correct"]} for r in rows if r["_id"]}

    async def _get_topic_breakdown(
        self, user_id: str, attempt_collection: str, item_collection: str, id_field: str, subject_id: str
    ) -> Dict[str, Dict[str, Any]]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }},
            {"$lookup": {
                "from": item_collection,
                "localField": "_id",
                "foreignField": id_field,
                "as": "item",
            }},
            {"$unwind": "$item"},
            {"$match": {"item.subject_id": subject_id}},
            {"$group": {
                "_id": "$item.topic_id",
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }},
        ]
        rows = await self._db[attempt_collection].aggregate(pipeline).to_list(None)
        return {r["_id"]: {"solved": r["solved"], "correct": r["correct"]} for r in rows if r["_id"]}
