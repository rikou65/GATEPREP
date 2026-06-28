from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from shared import YOUTUBE_API_KEY, async_get, db, err, get_current_user, iso, logger, new_id, now_utc, ok

router = APIRouter()

YT_BASE = "https://www.googleapis.com/youtube/v3"


def _extract_playlist_id(url: str) -> Optional[str]:
    import re
    m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def _iso8601_to_seconds(d: str) -> int:
    import re
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "PT0S")
    if not m:
        return 0
    days, h, mi, s = m.groups()
    return (int(days or 0))*86400 + (int(h or 0))*3600 + (int(mi or 0))*60 + int(s or 0)


async def _yt_fetch_playlist_meta(pid: str) -> Optional[Dict[str, Any]]:
    resp = await async_get(
        f"{YT_BASE}/playlists",
        params={"part": "snippet,contentDetails", "id": pid, "key": YOUTUBE_API_KEY},
        timeout=15,
    )
    r = resp.json()
    items = r.get("items") or []
    if not items:
        return None
    return {"snippet": items[0]["snippet"], "item_count": items[0]["contentDetails"]["itemCount"]}


async def _yt_fetch_playlist_items(pid: str) -> List[Dict[str, Any]]:
    videos: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    while True:
        params: Dict[str, Any] = {"part": "snippet,contentDetails", "playlistId": pid, "maxResults": 50, "key": YOUTUBE_API_KEY}
        if page_token:
            params["pageToken"] = page_token
        resp = await async_get(f"{YT_BASE}/playlistItems", params=params, timeout=15)
        page = resp.json()
        for it in page.get("items", []):
            videos.append({
                "youtube_video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "position": it["snippet"]["position"],
            })
        page_token = page.get("nextPageToken")
        if not page_token:
            return videos


async def _yt_fetch_video_durations(video_ids: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        resp = await async_get(
            f"{YT_BASE}/videos",
            params={"part": "contentDetails", "id": ",".join(chunk), "key": YOUTUBE_API_KEY},
            timeout=15,
        )
        rv = resp.json()
        for it in rv.get("items", []):
            out[it["id"]] = _iso8601_to_seconds(it["contentDetails"]["duration"])
    return out


def _build_playlist_doc(user_id: str, subject_id: str, pid: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    snip = meta["snippet"]
    thumbs = snip.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("default", {})).get("url", "")
    return {
        "playlist_id": new_id("pl"), "user_id": user_id, "subject_id": subject_id,
        "youtube_playlist_id": pid, "title": snip["title"], "thumbnail": thumb,
        "channel_title": snip.get("channelTitle", ""),
        "video_count": meta["item_count"], "created_at": iso(now_utc()),
    }


def _build_video_docs(playlist_id: str, videos: List[Dict[str, Any]], durations: Dict[str, int]) -> List[Dict[str, Any]]:
    return [{
        "video_id": new_id("vid"), "playlist_id": playlist_id,
        "youtube_video_id": v["youtube_video_id"], "title": v["title"],
        "position": v["position"], "duration": durations.get(v["youtube_video_id"], 0),
    } for v in videos]


from pydantic import BaseModel

class PlaylistImportIn(BaseModel):
    youtube_url: str
    subject_id: str


class VideoProgressIn(BaseModel):
    watch_percentage: float
    watch_time: int = 0


@router.post("/playlists/import")
async def import_playlist(body: PlaylistImportIn, user=Depends(get_current_user)):
    pid = _extract_playlist_id(body.youtube_url)
    if not pid:
        return err("invalid_url", "Invalid YouTube playlist URL", 400)
    if not YOUTUBE_API_KEY:
        return err("config", "YOUTUBE_API_KEY not configured", 500)
    existing = await db.playlists.find_one({"user_id": user["user_id"], "youtube_playlist_id": pid}, {"_id": 0})
    if existing:
        return ok(existing)
    try:
        meta = await _yt_fetch_playlist_meta(pid)
        if not meta:
            return err("not_found", "Playlist not found on YouTube", 404)
        videos = await _yt_fetch_playlist_items(pid)
        durations = await _yt_fetch_video_durations([v["youtube_video_id"] for v in videos])
    except Exception as e:
        logger.error(f"yt error: {e}")
        return err("youtube_error", str(e), 502)

    playlist = _build_playlist_doc(user["user_id"], body.subject_id, pid, meta)
    await db.playlists.insert_one(dict(playlist))
    playlist.pop("_id", None)
    video_docs = _build_video_docs(playlist["playlist_id"], videos, durations)
    if video_docs:
        await db.videos.insert_many([dict(v) for v in video_docs])
    return ok(playlist)


@router.get("/playlists")
async def my_playlists(subject_id: Optional[str] = None, user=Depends(get_current_user)):
    uid = user["user_id"]
    q: Dict[str, Any] = {"user_id": uid}
    if subject_id:
        q["subject_id"] = subject_id
    
    pipeline = [
        {"$match": q},
        {"$sort": {"created_at": -1}},
        {"$lookup": {
            "from": "videos",
            "localField": "playlist_id",
            "foreignField": "playlist_id",
            "as": "vids"
        }},
        {"$lookup": {
            "from": "video_progress",
            "let": {"user_id": uid, "vid_ids": "$vids.video_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$user_id", "$$user_id"]},
                    {"$in": ["$video_id", "$$vid_ids"]},
                    {"$eq": ["$completed", True]}
                ]}}}
            ],
            "as": "prog"
        }},
        {"$addFields": {
            "completed_videos": {"$size": "$prog"}
        }},
        {"$project": {"_id": 0, "vids": 0, "prog": 0}}
    ]
    docs = await db.playlists.aggregate(pipeline).to_list(500)
    return ok(docs)


@router.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: str, user=Depends(get_current_user)):
    p = await db.playlists.find_one({"playlist_id": playlist_id, "user_id": user["user_id"]}, {"_id": 0})
    if not p:
        return err("not_found", "Playlist not found", 404)
    videos = await db.videos.find({"playlist_id": playlist_id}, {"_id": 0}).sort("position", 1).to_list(2000)
    vid_ids = [v["video_id"] for v in videos]
    prog = await db.video_progress.find({"user_id": user["user_id"], "video_id": {"$in": vid_ids}}, {"_id": 0}).to_list(2000)
    pmap = {x["video_id"]: x for x in prog}
    for v in videos:
        v["progress"] = pmap.get(v["video_id"], {"watch_percentage": 0, "completed": False, "watch_time": 0})
    p["videos"] = videos
    return ok(p)


@router.delete("/playlists/{playlist_id}")
async def delete_playlist(playlist_id: str, user=Depends(get_current_user)):
    p = await db.playlists.find_one({"playlist_id": playlist_id, "user_id": user["user_id"]}, {"_id": 0})
    if not p:
        return err("not_found", "Not found", 404)
    vids = await db.videos.find({"playlist_id": playlist_id}, {"_id": 0, "video_id": 1}).to_list(2000)
    vid_ids = [v["video_id"] for v in vids]
    await db.video_progress.delete_many({"user_id": user["user_id"], "video_id": {"$in": vid_ids}})
    await db.videos.delete_many({"playlist_id": playlist_id})
    await db.playlists.delete_one({"playlist_id": playlist_id})
    return ok({"deleted": True})


@router.post("/videos/{video_id}/progress")
async def update_video_progress(video_id: str, body: VideoProgressIn, user=Depends(get_current_user)):
    completed = body.watch_percentage >= 90
    await db.video_progress.update_one(
        {"user_id": user["user_id"], "video_id": video_id},
        {"$set": {"watch_percentage": body.watch_percentage, "completed": completed,
                  "watch_time": body.watch_time, "last_watched_at": iso(now_utc())},
         "$setOnInsert": {"progress_id": new_id("prog"), "user_id": user["user_id"],
                          "video_id": video_id, "created_at": iso(now_utc())}},
        upsert=True,
    )
    return ok({"watch_percentage": body.watch_percentage, "completed": completed})


class VideoNotesIn(BaseModel):
    note_content: str


@router.get("/videos/{video_id}/notes")
async def get_video_notes(video_id: str, user=Depends(get_current_user)):
    n = await db.video_notes.find_one({"user_id": user["user_id"], "video_id": video_id}, {"_id": 0})
    return ok(n or {"note_content": "", "video_id": video_id})


@router.post("/videos/{video_id}/notes")
async def save_video_notes(video_id: str, body: VideoNotesIn, user=Depends(get_current_user)):
    await db.video_notes.update_one(
        {"user_id": user["user_id"], "video_id": video_id},
        {"$set": {"note_content": body.note_content, "updated_at": iso(now_utc())},
         "$setOnInsert": {"note_id": new_id("vnote"), "user_id": user["user_id"],
                          "video_id": video_id, "created_at": iso(now_utc())}},
        upsert=True,
    )
    return ok({"saved": True})

