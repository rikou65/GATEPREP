from __future__ import annotations

import asyncio
from copy import deepcopy
from time import monotonic
from typing import Any, Dict, List, Optional

from app.repositories.analytics import AnalyticsRepository
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

DASHBOARD_CACHE_TTL_SECONDS = 20.0
_dashboard_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self._repo = repo

    async def get_dashboard(self, user_id: str) -> Dict[str, Any]:
        cached = _dashboard_cache.get(user_id)
        now = monotonic()
        if cached and now - cached[0] < DASHBOARD_CACHE_TTL_SECONDS:
            return deepcopy(cached[1])

        async def collect_counts() -> Dict[str, int]:
            playlists, videos_done, mistakes, resources = await asyncio.gather(
                self._repo.count("playlists", {"user_id": user_id}),
                self._repo.count(
                    "video_progress", {"user_id": user_id, "completed": True}
                ),
                self._repo.count("mistakes", {"user_id": user_id}),
                self._repo.count("resources", {"user_id": user_id}),
            )
            return {
                "playlists": playlists,
                "videos_done": videos_done,
                "mistakes": mistakes,
                "resources": resources,
            }

        async def collect_subject_totals(collection: str) -> Dict[str, int]:
            return {
                r["_id"]: r["count"]
                async for r in self._repo.aggregate_cursor(
                    collection, subject_total_pipeline(user_id)
                )
            }

        (
            q_stats,
            p_stats,
            counts,
            subjects,
            q_totals,
            p_totals,
            q_progress,
            p_progress,
            recent,
        ) = await asyncio.gather(
            self._repo.get_latest_attempt_stats(
                user_id, "question_attempts", "question_id"
            ),
            self._repo.get_latest_attempt_stats(
                user_id, "pyq_attempts", "pyq_id"
            ),
            collect_counts(),
            self._repo.find_all(
                "subjects", {}, {"_id": 0, "subject_id": 1, "name": 1, "order": 1}
            ),
            collect_subject_totals("questions"),
            collect_subject_totals("pyqs"),
            self._repo.get_subject_breakdown(
                user_id, "question_attempts", "questions", "question_id"
            ),
            self._repo.get_subject_breakdown(
                user_id, "pyq_attempts", "pyqs", "pyq_id"
            ),
            self._get_recent_activity(user_id),
        )

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

        result = {"summary": summary, "subjects": overview, "recent_activity": recent}
        _dashboard_cache[user_id] = (now, deepcopy(result))
        return result

    async def _get_recent_activity(self, user_id: str) -> list:
        qa_recent, pa_recent = await asyncio.gather(
            self._repo.aggregate(
                "question_attempts", recent_question_activity_pipeline(user_id)
            ),
            self._repo.aggregate("pyq_attempts", recent_pyq_activity_pipeline(user_id)),
        )

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
            async for r in self._repo.aggregate_cursor(
                "questions", topic_total_pipeline(user_id, subject_id)
            )
        }
        p_totals = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor(
                "pyqs", topic_total_pipeline(user_id, subject_id)
            )
        }

        q_progress = await self._repo.get_topic_breakdown(
            user_id, "question_attempts", "questions", "question_id", subject_id
        )
        p_progress = await self._repo.get_topic_breakdown(
            user_id, "pyq_attempts", "pyqs", "pyq_id", subject_id
        )

        qids_by_topic: Dict[str, list] = {}
        async for q in self._repo.aggregate_cursor(
            "questions", question_ids_by_topic_pipeline(subject_id)
        ):
            qids_by_topic.setdefault(q["topic_id"], []).append(
                q["question_id"]
            )

        all_qids = [q for qids in qids_by_topic.values() for q in qids]
        noted_qids = set()
        if all_qids:
            async for note in self._repo.aggregate_cursor(
                "question_notes",
                notes_by_question_pipeline(user_id, all_qids),
            ):
                noted_qids.add(note["_id"])
        notes_count: Dict[str, int] = {
            tid: sum(1 for q in qids if q in noted_qids)
            for tid, qids in qids_by_topic.items()
        }

        mistakes_count = {
            r["_id"]: r["count"]
            async for r in self._repo.aggregate_cursor(
                "mistakes", mistakes_by_topic_pipeline(user_id, subject_id)
            )
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
            res = await self._repo.aggregate(
                coll, single_topic_stats_pipeline(user_id, topic_id, id_f, item_coll)
            )
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
            async for q in self._repo.aggregate_cursor(
                "questions", question_ids_for_topic_pipeline(topic_id)
            )
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
