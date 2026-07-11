from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.core.ids import new_id
from app.core.time import iso, now_utc
from app.repositories.playlists import (
    PlaylistRepository,
    VideoNoteRepository,
    VideoProgressRepository,
    VideoRepository,
)

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
    ):
        self._playlist_repo = playlist_repo
        self._video_repo = video_repo
        self._progress_repo = progress_repo
        self._note_repo = note_repo

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
