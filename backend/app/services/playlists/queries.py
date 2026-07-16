from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.playlists import (
    PlaylistRepository,
    VideoProgressRepository,
    VideoRepository,
)


def compute_duration_stats(
    vids: List[Dict[str, Any]], prog: List[Dict[str, Any]]
):
    pmap = {x["video_id"]: x for x in prog}
    total = sum(v.get("duration", 0) for v in vids)
    watched = 0
    completed = 0
    for v in vids:
        p = pmap.get(v["video_id"])
        dur = v.get("duration", 0)
        if p and p.get("completed"):
            watched += dur
            completed += 1
        elif p:
            watched += min(p.get("watch_time", 0), dur)
    return total, watched, completed


class PlaylistQueries:
    def __init__(
        self,
        playlist_repo: PlaylistRepository,
        video_repo: VideoRepository,
        progress_repo: VideoProgressRepository,
    ):
        self._playlist_repo = playlist_repo
        self._video_repo = video_repo
        self._progress_repo = progress_repo

    async def list_playlists(
        self, user_id: str, subject_id: Optional[str] = None, yt_refresh_cb=None
    ) -> List[Dict[str, Any]]:
        docs = await self._playlist_repo.list_summaries(user_id, subject_id)
        needs_refresh = []
        for doc in docs:
            doc.pop("_id", None)
            vids = doc.pop("vids", [])
            prog = doc.pop("prog", [])
            total, watched, completed_count = compute_duration_stats(
                vids, prog
            )
            doc["total_duration"] = total
            doc["watched_duration"] = watched
            doc["completed_videos"] = completed_count
            if total == 0 and doc.get("video_count", 0) > 0:
                needs_refresh.append(doc["playlist_id"])

        if needs_refresh and yt_refresh_cb:
            await yt_refresh_cb(user_id, needs_refresh)
            for doc in docs:
                pid = doc["playlist_id"]
                if pid not in needs_refresh:
                    continue
                vids = await self._video_repo.list_by_playlist(pid)
                vid_ids = [v["video_id"] for v in vids]
                prog = await self._progress_repo.find_by_video_ids(
                    user_id, vid_ids
                )
                total, watched, completed_count = compute_duration_stats(
                    vids, prog
                )
                doc["total_duration"] = total
                doc["watched_duration"] = watched
                doc["completed_videos"] = completed_count

        return docs

    async def get_playlist(
        self, user_id: str, playlist_id: str, yt_refresh_cb=None
    ) -> Optional[Dict[str, Any]]:
        p = await self._playlist_repo.find_by_id(playlist_id, user_id)
        if not p:
            return None

        videos = await self._video_repo.list_by_playlist(playlist_id)
        if any(v.get("duration", 0) == 0 for v in videos) and yt_refresh_cb:
            await yt_refresh_cb(user_id, [playlist_id])
            videos = await self._video_repo.list_by_playlist(playlist_id)

        vid_ids = [v["video_id"] for v in videos]
        prog = await self._progress_repo.find_by_video_ids(user_id, vid_ids)
        pmap = {x["video_id"]: x for x in prog}
        for v in videos:
            v["progress"] = pmap.get(
                v["video_id"],
                {
                    "watch_percentage": 0,
                    "completed": False,
                    "watch_time": 0,
                    "last_watched_at": None,
                },
            )
        p["videos"] = videos
        return p
