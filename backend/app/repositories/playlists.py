from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.playlist_queries import playlist_summary_pipeline


class PlaylistRepository:
    def __init__(self, db):
        self._db = db

    async def find_by_id(self, playlist_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.playlists.find_one(
            {"playlist_id": playlist_id, "user_id": user_id}, {"_id": 0}
        )

    async def find_by_youtube_id(self, user_id: str, youtube_playlist_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.playlists.find_one(
            {"user_id": user_id, "youtube_playlist_id": youtube_playlist_id}, {"_id": 0}
        )

    async def owns_playlist(self, user_id: str, playlist_id: str) -> bool:
        doc = await self._db.playlists.find_one(
            {"playlist_id": playlist_id, "user_id": user_id},
            {"_id": 1},
        )
        return doc is not None

    async def create(self, doc: Dict[str, Any]) -> None:
        await self._db.playlists.insert_one(dict(doc))

    async def delete(self, playlist_id: str) -> None:
        await self._db.playlists.delete_one({"playlist_id": playlist_id})

    async def list_summaries(
        self, user_id: str, subject_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        pipeline = playlist_summary_pipeline(user_id, subject_id)
        return await self._db.playlists.aggregate(pipeline).to_list(500)


class VideoRepository:
    def __init__(self, db):
        self._db = db

    async def find_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.videos.find_one({"video_id": video_id}, {"_id": 0})

    async def list_by_playlist(self, playlist_id: str) -> List[Dict[str, Any]]:
        return await self._db.videos.find(
            {"playlist_id": playlist_id}, {"_id": 0}
        ).sort("position", 1).to_list(2000)

    async def create_many(self, docs: List[Dict[str, Any]]) -> None:
        if docs:
            await self._db.videos.insert_many([dict(d) for d in docs])

    async def delete_by_playlist(self, playlist_id: str) -> None:
        await self._db.videos.delete_many({"playlist_id": playlist_id})

    async def find_with_zero_duration(self, playlist_id: str) -> List[Dict[str, Any]]:
        return await self._db.videos.find(
            {"playlist_id": playlist_id, "duration": {"$in": [None, 0]}},
            {"_id": 0, "youtube_video_id": 1},
        ).to_list(2000)

    async def find_zero_duration_by_playlists(
        self, playlist_ids: List[str]
    ) -> List[Dict[str, Any]]:
        if not playlist_ids:
            return []
        return await self._db.videos.find(
            {
                "playlist_id": {"$in": playlist_ids},
                "duration": {"$in": [None, 0]},
            },
            {"_id": 0, "playlist_id": 1, "youtube_video_id": 1},
        ).to_list(5000)

    async def update_duration(self, playlist_id: str, youtube_video_id: str, duration: int) -> None:
        await self._db.videos.update_one(
            {"playlist_id": playlist_id, "youtube_video_id": youtube_video_id},
            {"$set": {"duration": duration}},
        )


class VideoProgressRepository:
    def __init__(self, db):
        self._db = db

    async def find(self, user_id: str, video_id: str, projection: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        return await self._db.video_progress.find_one(
            {"user_id": user_id, "video_id": video_id},
            projection or {"_id": 0},
        )

    async def find_by_video_ids(self, user_id: str, video_ids: List[str]) -> List[Dict[str, Any]]:
        return await self._db.video_progress.find(
            {"user_id": user_id, "video_id": {"$in": video_ids}},
            {"_id": 0},
        ).to_list(2000)

    async def upsert(self, user_id: str, video_id: str, data: Dict[str, Any]) -> None:
        from app.core.ids import new_id
        from app.core.time import iso, now_utc

        await self._db.video_progress.update_one(
            {"user_id": user_id, "video_id": video_id},
            {"$set": {**data, "last_watched_at": iso(now_utc())},
             "$setOnInsert": {
                 "progress_id": new_id("prog"),
                 "user_id": user_id,
                 "video_id": video_id,
                 "created_at": iso(now_utc()),
             }},
            upsert=True,
        )

    async def delete_by_video_ids(self, user_id: str, video_ids: List[str]) -> None:
        await self._db.video_progress.delete_many(
            {"user_id": user_id, "video_id": {"$in": video_ids}}
        )


class VideoNoteRepository:
    def __init__(self, db):
        self._db = db

    async def find(self, user_id: str, video_id: str) -> Optional[Dict[str, Any]]:
        return await self._db.video_notes.find_one(
            {"user_id": user_id, "video_id": video_id}, {"_id": 0}
        )

    async def upsert(self, user_id: str, video_id: str, content: str) -> None:
        from app.core.ids import new_id
        from app.core.time import iso, now_utc

        await self._db.video_notes.update_one(
            {"user_id": user_id, "video_id": video_id},
            {
                "$set": {"note_content": content, "updated_at": iso(now_utc())},
                "$setOnInsert": {
                    "note_id": new_id("vnote"),
                    "user_id": user_id,
                    "video_id": video_id,
                    "created_at": iso(now_utc()),
                },
            },
            upsert=True,
        )

    async def delete_by_video_ids(self, user_id: str, video_ids: List[str]) -> None:
        await self._db.video_notes.delete_many(
            {"user_id": user_id, "video_id": {"$in": video_ids}}
        )
