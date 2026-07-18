from __future__ import annotations

import re
from typing import Any, Dict, List


class SearchRepository:
    def __init__(self, db):
        self._db = db

    @staticmethod
    def _contains(query: str) -> Dict[str, str]:
        return {"$regex": re.escape(query.strip()), "$options": "i"}

    async def subjects(self, query: str, limit: int) -> List[Dict[str, Any]]:
        return (
            await self._db.subjects.find(
                {"name": self._contains(query)},
                {"_id": 0, "subject_id": 1, "name": 1, "order": 1},
            )
            .sort("order", 1)
            .to_list(limit)
        )

    async def topics(self, query: str, limit: int) -> List[Dict[str, Any]]:
        return (
            await self._db.topics.find(
                {"name": self._contains(query)},
                {"_id": 0, "topic_id": 1, "subject_id": 1, "name": 1, "order": 1},
            )
            .sort("order", 1)
            .to_list(limit)
        )

    async def questions(
        self, user_id: str, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        rx = self._contains(query)
        return await self._db.questions.find(
            {
                "user_id": user_id,
                "$or": [
                    {"question_text": rx},
                    {"solution": rx},
                    {"source": rx},
                    {"question_type": rx},
                ],
            },
            {
                "_id": 0,
                "question_id": 1,
                "subject_id": 1,
                "topic_id": 1,
                "question_type": 1,
                "question_text": 1,
                "source": 1,
            },
        ).to_list(limit)

    async def pyqs(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        rx = self._contains(query)
        return await self._db.pyqs.find(
            {
                "user_id": user_id,
                "$or": [
                    {"question_text": rx},
                    {"solution": rx},
                    {"source": rx},
                    {"question_type": rx},
                    {"gate_set": rx},
                    {"gate_qnum": rx},
                ],
            },
            {
                "_id": 0,
                "pyq_id": 1,
                "subject_id": 1,
                "topic_id": 1,
                "question_type": 1,
                "question_text": 1,
                "source": 1,
                "year": 1,
            },
        ).to_list(limit)

    async def resources(
        self, user_id: str, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        rx = self._contains(query)
        return await self._db.resources.find(
            {
                "user_id": user_id,
                "$or": [
                    {"title": rx},
                    {"filename": rx},
                    {"resource_type": rx},
                    {"source": rx},
                ],
            },
            {
                "_id": 0,
                "resource_id": 1,
                "subject_id": 1,
                "title": 1,
                "filename": 1,
                "resource_type": 1,
                "source": 1,
            },
        ).sort("created_at", -1).to_list(limit)

    async def playlists(
        self, user_id: str, query: str, limit: int
    ) -> List[Dict[str, Any]]:
        rx = self._contains(query)
        return await self._db.playlists.find(
            {
                "user_id": user_id,
                "$or": [{"title": rx}, {"channel_title": rx}],
            },
            {
                "_id": 0,
                "playlist_id": 1,
                "subject_id": 1,
                "title": 1,
                "channel_title": 1,
                "video_count": 1,
            },
        ).sort("created_at", -1).to_list(limit)

    async def videos(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        playlist_docs = await self._db.playlists.find(
            {"user_id": user_id}, {"_id": 0, "playlist_id": 1, "title": 1}
        ).to_list(2000)
        playlist_titles = {
            doc["playlist_id"]: doc.get("title", "") for doc in playlist_docs
        }
        playlist_ids = list(playlist_titles)
        if not playlist_ids:
            return []

        videos = await self._db.videos.find(
            {
                "playlist_id": {"$in": playlist_ids},
                "title": self._contains(query),
            },
            {
                "_id": 0,
                "video_id": 1,
                "playlist_id": 1,
                "title": 1,
                "position": 1,
            },
        ).sort("position", 1).to_list(limit)
        for video in videos:
            video["playlist_title"] = playlist_titles.get(video.get("playlist_id"), "")
        return videos
