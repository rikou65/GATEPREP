from __future__ import annotations

import asyncio
from copy import deepcopy
from time import monotonic
from typing import Any, Dict, List, Optional

from app.repositories.analytics import AnalyticsRepository

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
            self._repo.get_latest_qbank_attempt_stats(user_id),
            self._repo.get_latest_pyq_attempt_stats(user_id),
            self._repo.count_user_dashboard_items(user_id),
            self._repo.list_subjects(),
            self._repo.get_qbank_subject_totals(user_id),
            self._repo.get_pyq_subject_totals(user_id),
            self._repo.get_qbank_subject_breakdown(user_id),
            self._repo.get_pyq_subject_breakdown(user_id),
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
            self._repo.get_recent_question_activity(user_id),
            self._repo.get_recent_pyq_activity(user_id),
        )

        merged = [
            {"type": "question", **a} for a in qa_recent
        ] + [{"type": "pyq", **a} for a in pa_recent]
        return sorted(merged, key=lambda x: x["attempted_at"], reverse=True)[:10]

    async def get_subject_analytics(
        self, user_id: str, subject_id: str
    ) -> List[Dict[str, Any]]:
        (
            topics,
            q_totals,
            p_totals,
            q_progress,
            p_progress,
            qids_by_topic,
            mistakes_count,
        ) = await asyncio.gather(
            self._repo.list_topics_for_subject(subject_id),
            self._repo.get_qbank_topic_totals(user_id, subject_id),
            self._repo.get_pyq_topic_totals(user_id, subject_id),
            self._repo.get_qbank_topic_breakdown(user_id, subject_id),
            self._repo.get_pyq_topic_breakdown(user_id, subject_id),
            self._repo.get_question_ids_by_topic(subject_id),
            self._repo.get_mistake_counts_by_topic(user_id, subject_id),
        )

        all_qids = [q for qids in qids_by_topic.values() for q in qids]
        noted_qids = await self._repo.get_noted_question_ids(user_id, all_qids)
        notes_count: Dict[str, int] = {
            tid: sum(1 for q in qids if q in noted_qids)
            for tid, qids in qids_by_topic.items()
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
        t = await self._repo.find_topic(topic_id)
        if not t:
            return None

        qb_t, pyq_t, qb_p, pyq_p, qids = await asyncio.gather(
            self._repo.count_qbank_for_topic(user_id, topic_id),
            self._repo.count_pyqs_for_topic(user_id, topic_id),
            self._repo.get_qbank_topic_stats(user_id, topic_id),
            self._repo.get_pyq_topic_stats(user_id, topic_id),
            self._repo.get_question_ids_for_topic(topic_id),
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

        notes, mis = await asyncio.gather(
            self._repo.count_notes_for_questions(user_id, qids),
            self._repo.count_mistakes_for_topic(user_id, topic_id),
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
