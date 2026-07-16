from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.integrations.google_youtube import (
    YouTubeAPI,
    YouTubeAPIError,
    YouTubeTokenManager,
)
from app.repositories.playlists import (
    PlaylistRepository,
    VideoNoteRepository,
    VideoProgressRepository,
    VideoRepository,
)
from app.repositories.youtube import YouTubeCredentialRepository

YT_BASE = "https://www.googleapis.com/youtube/v3"


def extract_playlist_id(url: str) -> Optional[str]:
    m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def iso8601_to_seconds(d: str) -> int:
    m = re.match(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "PT0S"
    )
    if not m:
        return 0
    days, h, mi, s = m.groups()
    return (
        (int(days or 0)) * 86400
        + (int(h or 0)) * 3600
        + (int(mi or 0)) * 60
        + int(s or 0)
    )


def build_playlist_doc(
    user_id: str, subject_id: str, pid: str, meta: Dict[str, Any]
) -> Dict[str, Any]:
    snip = meta["snippet"]
    thumbs = snip.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("default", {})).get("url", "")
    return {
        "playlist_id": new_id("pl"),
        "user_id": user_id,
        "subject_id": subject_id,
        "youtube_playlist_id": pid,
        "title": snip["title"],
        "thumbnail": thumb,
        "channel_title": snip.get("channelTitle", ""),
        "video_count": meta["item_count"],
        "created_at": iso(now_utc()),
    }


def build_video_docs(
    playlist_id: str,
    videos: List[Dict[str, Any]],
    durations: Dict[str, int],
) -> List[Dict[str, Any]]:
    return [
        {
            "video_id": new_id("vid"),
            "playlist_id": playlist_id,
            "youtube_video_id": v["youtube_video_id"],
            "title": v["title"],
            "position": v["position"],
            "duration": durations.get(v["youtube_video_id"], 0),
        }
        for v in videos
    ]


class PlaylistCommands:
    def __init__(
        self,
        playlist_repo: PlaylistRepository,
        video_repo: VideoRepository,
        progress_repo: VideoProgressRepository,
        note_repo: VideoNoteRepository,
        youtube_repo: YouTubeCredentialRepository,
        youtube_token_manager: YouTubeTokenManager,
        youtube_api: YouTubeAPI,
    ):
        self._playlist_repo = playlist_repo
        self._video_repo = video_repo
        self._progress_repo = progress_repo
        self._note_repo = note_repo
        self._youtube_repo = youtube_repo
        self._youtube_token_manager = youtube_token_manager
        self._youtube_api = youtube_api

    async def import_from_youtube_url(
        self,
        user_id: str,
        youtube_url: str,
        subject_id: str,
    ) -> Dict[str, Any]:
        if not extract_playlist_id(youtube_url):
            return {
                "error": "invalid_url",
                "message": "Invalid YouTube playlist URL",
                "status_code": 400,
            }

        yt_token = await self._youtube_token_manager.get_token(
            user_id, self._youtube_repo
        )
        if not yt_token:
            return {
                "error": "youtube_not_connected",
                "message": "Connect YouTube in Settings first",
                "status_code": 400,
            }

        try:
            result = await self.import_playlist(
                user_id,
                youtube_url,
                subject_id,
                yt_token,
                self._youtube_api,
            )
        except YouTubeAPIError as exc:
            if exc.clear_credentials:
                await self._youtube_repo.delete(user_id)
            return {
                "error": exc.code,
                "message": exc.message,
                "status_code": exc.status_code,
            }

        if result is None:
            return {
                "error": "invalid_url",
                "message": "Invalid YouTube playlist URL",
                "status_code": 400,
            }
        if isinstance(result, dict) and result.get("error") == "not_found":
            return {
                "error": "not_found",
                "message": "Playlist not found on YouTube",
                "status_code": 404,
            }
        if isinstance(result, dict) and result.get("error"):
            return {
                "error": result["error"],
                "message": result.get("msg", "Unknown YouTube error"),
                "status_code": 502,
            }
        return result

    async def refresh_missing_durations(
        self,
        user_id: str,
        playlist_ids: list,
    ) -> None:
        token = await self._youtube_token_manager.get_token(
            user_id, self._youtube_repo
        )
        if not token:
            return
        videos = await self._video_repo.find_zero_duration_by_playlists(
            playlist_ids
        )
        if not videos:
            return
        youtube_ids = [v["youtube_video_id"] for v in videos]
        try:
            durations = await self._youtube_api.fetch_video_durations(
                youtube_ids, token
            )
        except Exception:
            return
        for v in videos:
            duration = durations.get(v["youtube_video_id"])
            if duration and duration > 0:
                await self._video_repo.update_duration(
                    v["playlist_id"], v["youtube_video_id"], duration
                )

    async def import_playlist(
        self,
        user_id: str,
        youtube_url: str,
        subject_id: str,
        yt_token: str | None,
        yt_api: Any,
    ) -> Optional[Dict[str, Any]]:
        pid = extract_playlist_id(youtube_url)
        if not pid:
            return None
        if not yt_token:
            return {"error": "youtube_not_connected"}

        existing = await self._playlist_repo.find_by_youtube_id(user_id, pid)
        if existing:
            return {**existing, "already_exists": True}

        meta = await yt_api.fetch_playlist_meta(pid, yt_token)
        if not meta:
            return {"error": "not_found"}

        videos = await yt_api.fetch_playlist_items(pid, yt_token)
        yt_ids = [v["youtube_video_id"] for v in videos]
        durations = await yt_api.fetch_video_durations(yt_ids, yt_token)

        playlist = build_playlist_doc(user_id, subject_id, pid, meta)
        await self._playlist_repo.create(playlist)
        video_docs = build_video_docs(
            playlist["playlist_id"], videos, durations
        )
        await self._video_repo.create_many(video_docs)
        return playlist

    async def delete_playlist(self, user_id: str, playlist_id: str) -> bool:
        p = await self._playlist_repo.find_by_id(playlist_id, user_id)
        if not p:
            return False
        vids = await self._video_repo.list_by_playlist(playlist_id)
        vid_ids = [v["video_id"] for v in vids]
        if vid_ids:
            await self._progress_repo.delete_by_video_ids(user_id, vid_ids)
            await self._note_repo.delete_by_video_ids(user_id, vid_ids)
        await self._video_repo.delete_by_playlist(playlist_id)
        await self._playlist_repo.delete(playlist_id)
        return True

    async def update_progress(
        self,
        user_id: str,
        video_id: str,
        watch_percentage: float,
        watch_time: int,
        completed: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        v = await self._video_repo.find_by_id(video_id)
        if not v:
            return None
        if not await self._playlist_repo.owns_playlist(user_id, v["playlist_id"]):
            return None

        if completed is not None:
            completed_val = completed
        else:
            existing = await self._progress_repo.find(
                user_id, video_id, {"completed": 1}
            )
            if existing and existing.get("completed") is True:
                completed_val = True
            else:
                completed_val = watch_percentage >= 90

        await self._progress_repo.upsert(
            user_id,
            video_id,
            {
                "watch_percentage": watch_percentage,
                "completed": completed_val,
                "watch_time": watch_time,
            },
        )
        return {
            "watch_percentage": watch_percentage,
            "completed": completed_val,
        }

    async def get_video_notes(
        self, user_id: str, video_id: str
    ) -> Optional[Dict[str, Any]]:
        v = await self._video_repo.find_by_id(video_id)
        if not v:
            return None
        if not await self._playlist_repo.owns_playlist(user_id, v["playlist_id"]):
            return None
        n = await self._note_repo.find(user_id, video_id)
        return n or {"note_content": "", "video_id": video_id}

    async def save_video_notes(
        self, user_id: str, video_id: str, note_content: str
    ) -> Optional[Dict[str, bool]]:
        v = await self._video_repo.find_by_id(video_id)
        if not v:
            return None
        if not await self._playlist_repo.owns_playlist(user_id, v["playlist_id"]):
            return None
        await self._note_repo.upsert(user_id, video_id, note_content)
        return {"saved": True}
