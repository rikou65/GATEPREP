from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from urllib.parse import urlencode

from app.repositories.search import SearchRepository


class SearchService:
    def __init__(self, repo: SearchRepository):
        self._repo = repo

    async def search(self, user_id: str, query: str, limit: int = 12) -> List[Dict[str, Any]]:
        term = query.strip()
        if len(term) < 2:
            return []

        per_type = max(3, min(8, limit))
        groups = await asyncio.gather(
            self._repo.subjects(term, per_type),
            self._repo.topics(term, per_type),
            self._repo.questions(user_id, term, per_type),
            self._repo.pyqs(user_id, term, per_type),
            self._repo.resources(user_id, term, per_type),
            self._repo.playlists(user_id, term, per_type),
            self._repo.videos(user_id, term, per_type),
        )

        results: List[Dict[str, Any]] = []
        mappers = (
            self._subject_result,
            self._topic_result,
            self._question_result,
            self._pyq_result,
            self._resource_result,
            self._playlist_result,
            self._video_result,
        )
        for docs, mapper in zip(groups, mappers):
            results.extend(mapper(doc) for doc in docs)
        return results[:limit]

    @staticmethod
    def _excerpt(value: Any, length: int = 120) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= length:
            return text
        return text[: length - 1].rstrip() + "…"

    @staticmethod
    def _with_params(path: str, params: Dict[str, Any]) -> str:
        clean = {key: value for key, value in params.items() if value}
        return f"{path}?{urlencode(clean)}" if clean else path

    def _subject_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "subject",
            "id": doc["subject_id"],
            "title": doc.get("name", "Subject"),
            "subtitle": "Subject",
            "url": f"/subjects/{doc['subject_id']}",
            "badge": "Subject",
        }

    def _topic_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "topic",
            "id": doc["topic_id"],
            "title": doc.get("name", "Topic"),
            "subtitle": "Topic",
            "url": f"/topics/{doc['topic_id']}",
            "badge": "Topic",
            "metadata": {"subject_id": doc.get("subject_id")},
        }

    def _question_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "question",
            "id": doc["question_id"],
            "title": self._excerpt(doc.get("question_text"), 80) or "Question",
            "subtitle": "Question Bank",
            "url": self._with_params(
                "/questions",
                {"subject_id": doc.get("subject_id"), "topic_id": doc.get("topic_id")},
            ),
            "excerpt": self._excerpt(doc.get("question_text")),
            "badge": doc.get("question_type") or "QBank",
        }

    def _pyq_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        year = doc.get("year")
        return {
            "type": "pyq",
            "id": doc["pyq_id"],
            "title": self._excerpt(doc.get("question_text"), 80) or "PYQ",
            "subtitle": f"PYQ{f' · {year}' if year else ''}",
            "url": self._with_params(
                "/pyqs",
                {
                    "subject_id": doc.get("subject_id"),
                    "topic_id": doc.get("topic_id"),
                    "year": year,
                },
            ),
            "excerpt": self._excerpt(doc.get("question_text")),
            "badge": str(year) if year else "PYQ",
        }

    def _resource_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "resource",
            "id": doc["resource_id"],
            "title": doc.get("title") or doc.get("filename") or "Resource",
            "subtitle": doc.get("resource_type") or "Resource",
            "url": self._with_params("/resources", {"subject_id": doc.get("subject_id")}),
            "excerpt": doc.get("filename") or "",
            "badge": "Resource",
        }

    def _playlist_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "playlist",
            "id": doc["playlist_id"],
            "title": doc.get("title", "Playlist"),
            "subtitle": doc.get("channel_title") or "Playlist",
            "url": f"/playlists/{doc['playlist_id']}",
            "badge": "Playlist",
            "metadata": {"video_count": doc.get("video_count")},
        }

    def _video_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "video",
            "id": doc["video_id"],
            "title": doc.get("title", "Video"),
            "subtitle": doc.get("playlist_title") or "Video",
            "url": f"/playlists/{doc['playlist_id']}",
            "badge": "Video",
        }
