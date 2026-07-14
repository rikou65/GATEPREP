from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.analytics import AnalyticsRepository


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self._repo = repo

    async def get_dashboard(self, user_id: str) -> Dict[str, Any]:
        q_stats = await self._repo.get_latest_attempt_stats(
            user_id, "question_attempts", "question_id"
        )
        p_stats = await self._repo.get_latest_attempt_stats(
            user_id, "pyq_attempts", "pyq_id"
        )

        counts = {
            "playlists": await self._repo.count(
                "playlists", {"user_id": user_id}
            ),
            "videos_done": await self._repo.count(
                "video_progress", {"user_id": user_id, "completed": True}
            ),
            "mistakes": await self._repo.count(
                "mistakes", {"user_id": user_id}
            ),
            "resources": await self._repo.count(
                "resources", {"user_id": user_id}
            ),
        }

        summary = {
            "questions_solved": q_stats["solved"],
            "pyqs_solved": p_stats["solved"],
            "videos_completed": counts["videos_done"],
            "total_playlists": counts["playlists"],
            "question_accuracy": q_stats["accuracy"],
            "pyq_accuracy": p_stats["accuracy"],
            "total_mistakes": counts["mistakes"],
            "resources_uploaded": counts["resources"],
        }

        subjects = await self._repo.find_all("subjects", {}, {"_id": 0, "subject_id": 1, "name": 1, "order": 1})

        q_totals = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor("questions", [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}},
            ])
        }
        p_totals = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor("pyqs", [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}},
            ])
        }

        q_progress = await self._repo.get_subject_breakdown(
            user_id, "question_attempts", "questions", "question_id"
        )
        p_progress = await self._repo.get_subject_breakdown(
            user_id, "pyq_attempts", "pyqs", "pyq_id"
        )

        overview = []
        for s in subjects:
            sid = s["subject_id"]
            qb_t = q_totals.get(sid, 0)
            qb_p = q_progress.get(sid, {"solved": 0, "correct": 0})
            qb_acc = (
                round(qb_p["correct"] / qb_p["solved"] * 100, 1)
                if qb_p["solved"] > 0
                else 0.0
            )
            pyq_t = p_totals.get(sid, 0)
            pyq_p = p_progress.get(sid, {"solved": 0, "correct": 0})
            pyq_acc = (
                round(pyq_p["correct"] / pyq_p["solved"] * 100, 1)
                if pyq_p["solved"] > 0
                else 0.0
            )
            overview.append({
                "subject": s,
                "qb": {
                    "total": qb_t,
                    "solved": qb_p["solved"],
                    "remaining": qb_t - qb_p["solved"],
                    "accuracy": qb_acc,
                },
                "pyq": {
                    "total": pyq_t,
                    "solved": pyq_p["solved"],
                    "remaining": pyq_t - pyq_p["solved"],
                    "accuracy": pyq_acc,
                },
            })

        recent = await self._get_recent_activity(user_id)
        return {"summary": summary, "subjects": overview, "recent_activity": recent}

    async def _get_recent_activity(self, user_id: str) -> list:
        qa_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$limit": 10},
            {"$lookup": {
                "from": "questions",
                "localField": "question_id",
                "foreignField": "question_id",
                "as": "q",
            }},
            {"$unwind": {"path": "$q", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {
                "from": "subjects",
                "localField": "q.subject_id",
                "foreignField": "subject_id",
                "as": "subj",
            }},
            {"$lookup": {
                "from": "topics",
                "localField": "q.topic_id",
                "foreignField": "topic_id",
                "as": "top",
            }},
            {"$project": {
                "_id": 0,
                "attempt_id": 1, "question_id": 1, "is_correct": 1,
                "time_taken": 1, "attempted_at": 1,
                "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
                "topic_name": {"$arrayElemAt": ["$top.name", 0]},
                "question_type": "$q.question_type",
            }},
        ]
        pa_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$limit": 10},
            {"$lookup": {
                "from": "pyqs",
                "localField": "pyq_id",
                "foreignField": "pyq_id",
                "as": "q",
            }},
            {"$unwind": {"path": "$q", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {
                "from": "subjects",
                "localField": "q.subject_id",
                "foreignField": "subject_id",
                "as": "subj",
            }},
            {"$lookup": {
                "from": "topics",
                "localField": "q.topic_id",
                "foreignField": "topic_id",
                "as": "top",
            }},
            {"$project": {
                "_id": 0,
                "attempt_id": 1, "pyq_id": 1, "is_correct": 1,
                "time_taken": 1, "attempted_at": 1,
                "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
                "topic_name": {"$arrayElemAt": ["$top.name", 0]},
                "question_type": "$q.question_type",
                "year": "$q.year",
            }},
        ]

        qa_recent = await self._repo.aggregate(
            "question_attempts", qa_pipeline
        )
        pa_recent = await self._repo.aggregate("pyq_attempts", pa_pipeline)

        merged = [
            {"type": "question", **a} for a in qa_recent
        ] + [{"type": "pyq", **a} for a in pa_recent]
        return sorted(merged, key=lambda x: x["attempted_at"], reverse=True)[:10]

    async def get_subject_analytics(
        self, user_id: str, subject_id: str
    ) -> List[Dict[str, Any]]:
        topics = await self._repo.find_all(
            "topics", {"subject_id": subject_id},
            {"_id": 0, "topic_id": 1, "name": 1, "order": 1},
        )

        q_totals = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor("questions", [
                {"$match": {"subject_id": subject_id, "user_id": user_id}},
                {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}},
            ])
        }
        p_totals = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor("pyqs", [
                {"$match": {"subject_id": subject_id, "user_id": user_id}},
                {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}},
            ])
        }

        q_progress = await self._repo.get_topic_breakdown(
            user_id, "question_attempts", "questions", "question_id", subject_id
        )
        p_progress = await self._repo.get_topic_breakdown(
            user_id, "pyq_attempts", "pyqs", "pyq_id", subject_id
        )

        qids_by_topic: Dict[str, list] = {}
        async for q in self._repo.aggregate_cursor("questions", [
            {"$match": {"subject_id": subject_id}},
            {"$project": {"question_id": 1, "topic_id": 1}},
        ]):
            qids_by_topic.setdefault(q["topic_id"], []).append(
                q["question_id"]
            )

        all_qids = [q for qids in qids_by_topic.values() for q in qids]
        noted_qids = set()
        if all_qids:
            async for note in self._repo.aggregate_cursor(
                "question_notes",
                [
                    {"$match": {"user_id": user_id, "question_id": {"$in": all_qids}}},
                    {"$group": {"_id": "$question_id"}},
                ],
            ):
                noted_qids.add(note["_id"])
        notes_count: Dict[str, int] = {
            tid: sum(1 for q in qids if q in noted_qids)
            for tid, qids in qids_by_topic.items()
        }

        mistakes_count = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor("mistakes", [
                {"$match": {"user_id": user_id, "subject_id": subject_id}},
                {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}},
            ])
        }

        rows = []
        for t in topics:
            tid = t["topic_id"]
            qb_t = q_totals.get(tid, 0)
            qb_p = q_progress.get(tid, {"solved": 0, "correct": 0})
            qb_acc = (
                round(qb_p["correct"] / qb_p["solved"] * 100, 1)
                if qb_p["solved"] > 0
                else 0.0
            )
            pyq_t = p_totals.get(tid, 0)
            pyq_p = p_progress.get(tid, {"solved": 0, "correct": 0})
            pyq_acc = (
                round(pyq_p["correct"] / pyq_p["solved"] * 100, 1)
                if pyq_p["solved"] > 0
                else 0.0
            )
            rows.append({
                "topic": t,
                "qb": {
                    "total": qb_t,
                    "solved": qb_p["solved"],
                    "remaining": qb_t - qb_p["solved"],
                    "accuracy": qb_acc,
                },
                "pyq": {
                    "total": pyq_t,
                    "solved": pyq_p["solved"],
                    "remaining": pyq_t - pyq_p["solved"],
                    "accuracy": pyq_acc,
                },
                "notes_count": notes_count.get(tid, 0),
                "mistakes_count": mistakes_count.get(tid, 0),
            })
        return rows

    async def get_topic_analytics(
        self, user_id: str, topic_id: str
    ) -> Optional[Dict[str, Any]]:
        t = await self._repo.find_one("topics", {"topic_id": topic_id})
        if not t:
            return None

        sid = t["subject_id"]
        qb_t = await self._repo.count(
            "questions", {"topic_id": topic_id, "user_id": user_id}
        )
        pyq_t = await self._repo.count(
            "pyqs", {"topic_id": topic_id, "user_id": user_id}
        )

        async def single_topic_stats(coll, id_f, item_coll):
            p = [
                {"$match": {"user_id": user_id}},
                {"$sort": {"attempted_at": -1}},
                {
                    "$group": {
                        "_id": f"${id_f}",
                        "is_correct": {"$first": "$is_correct"},
                    }
                },
                {
                    "$lookup": {
                        "from": item_coll,
                        "localField": "_id",
                        "foreignField": id_f,
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
            res = await self._repo.aggregate(coll, p)
            if not res:
                return {"solved": 0, "correct": 0}
            return {"solved": res[0]["solved"], "correct": res[0]["correct"]}

        qb_p = await single_topic_stats(
            "question_attempts", "question_id", "questions"
        )
        pyq_p = await single_topic_stats(
            "pyq_attempts", "pyq_id", "pyqs"
        )

        qb_acc = (
            round(qb_p["correct"] / qb_p["solved"] * 100, 1)
            if qb_p["solved"] > 0
            else 0.0
        )
        pyq_acc = (
            round(pyq_p["correct"] / pyq_p["solved"] * 100, 1)
            if pyq_p["solved"] > 0
            else 0.0
        )

        qids = [
            q["question_id"]
            async for q in self._repo.aggregate_cursor("questions", [
                {"$match": {"topic_id": topic_id}},
                {"$project": {"question_id": 1}},
            ])
        ]
        notes = await self._repo.count(
            "question_notes",
            {"user_id": user_id, "question_id": {"$in": qids}},
        )
        mis = await self._repo.count(
            "mistakes", {"user_id": user_id, "topic_id": topic_id}
        )

        return {
            "topic": t,
            "qb": {
                "total": qb_t,
                "solved": qb_p["solved"],
                "remaining": qb_t - qb_p["solved"],
                "accuracy": qb_acc,
            },
            "pyq": {
                "total": pyq_t,
                "solved": pyq_p["solved"],
                "remaining": pyq_t - pyq_p["solved"],
                "accuracy": pyq_acc,
            },
            "notes_count": notes,
            "mistakes_count": mis,
        }
