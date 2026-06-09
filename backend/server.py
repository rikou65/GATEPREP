"""GATE Study OS - FastAPI backend (MongoDB)."""
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import uuid
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
ADMIN_EMAILS = [e.strip() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]

app = FastAPI(title="GATE Study OS")
api = APIRouter(prefix="/api")

logger = logging.getLogger("gateos")
logging.basicConfig(level=logging.INFO)

# ---------- helpers ----------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def ok(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data}


def err(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "error": {"code": code, "message": message}},
    )

# ---------- auth ----------
async def get_current_user(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session")
    exp = sess.get("expires_at")
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now_utc():
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def require_admin(user=Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user

# ---------- Auth routes ----------
@api.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        return err("missing_session_id", "session_id required", 400)
    try:
        r = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}, timeout=15,
        )
        if r.status_code != 200:
            return err("auth_failed", "Failed to verify session", 401)
        data = r.json()
    except Exception as e:
        logger.error(f"auth error: {e}")
        return err("auth_failed", "Auth provider unreachable", 502)

    email = data["email"]
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data["name"], "picture": data.get("picture", "")}},
        )
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    else:
        user_id = new_id("user")
        is_admin = email in ADMIN_EMAILS or (await db.users.count_documents({})) == 0
        user = {
            "user_id": user_id,
            "email": email,
            "name": data["name"],
            "picture": data.get("picture", ""),
            "is_admin": is_admin,
            "created_at": iso(now_utc()),
        }
        await db.users.insert_one(dict(user))
        user.pop("_id", None)

    session_token = data["session_token"]
    expires_at = now_utc() + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token, "expires_at": iso(expires_at),
        "created_at": iso(now_utc()),
    })
    response.set_cookie(
        key="session_token", value=session_token, httponly=True,
        secure=True, samesite="none", path="/", max_age=7*24*3600,
    )
    return ok({"user": {k: v for k, v in user.items() if k != "_id"}})

@api.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    return ok({"user": {k: v for k, v in user.items() if k != "_id"}})

@api.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return ok({"logged_out": True})

# ---------- Subjects / Topics ----------
@api.get("/subjects")
async def list_subjects():
    docs = await db.subjects.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return ok(docs)

@api.get("/subjects/{subject_id}")
async def get_subject(subject_id: str):
    s = await db.subjects.find_one({"subject_id": subject_id}, {"_id": 0})
    if not s:
        return err("not_found", "Subject not found", 404)
    return ok(s)

@api.get("/subjects/{subject_id}/topics")
async def list_topics(subject_id: str):
    docs = await db.topics.find({"subject_id": subject_id}, {"_id": 0}).sort("order", 1).to_list(500)
    return ok(docs)

@api.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    t = await db.topics.find_one({"topic_id": topic_id}, {"_id": 0})
    if not t:
        return err("not_found", "Topic not found", 404)
    s = await db.subjects.find_one({"subject_id": t["subject_id"]}, {"_id": 0})
    t["subject"] = s
    return ok(t)

# ---------- Questions ----------
@api.get("/questions")
async def list_questions(
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    skip: int = 0,
    user=Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if subject_id:
        q["subject_id"] = subject_id
    if topic_id:
        q["topic_id"] = topic_id
    if difficulty:
        q["difficulty"] = difficulty
    if question_type:
        q["question_type"] = question_type
    total = await db.questions.count_documents(q)
    docs = await db.questions.find(q, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    # attach attempt summary per question for this user
    qids = [d["question_id"] for d in docs]
    attempts = await db.question_attempts.find(
        {"user_id": user["user_id"], "question_id": {"$in": qids}}, {"_id": 0}
    ).to_list(2000)
    by_q: Dict[str, Dict[str, Any]] = {}
    for a in attempts:
        cur = by_q.setdefault(a["question_id"], {"count": 0, "correct": 0, "last_correct": None})
        cur["count"] += 1
        if a["is_correct"]:
            cur["correct"] += 1
        cur["last_correct"] = a["is_correct"]
    for d in docs:
        d["user_progress"] = by_q.get(d["question_id"], {"count": 0, "correct": 0, "last_correct": None})
    return ok({"items": docs, "total": total})

@api.get("/questions/{question_id}")
async def get_question(question_id: str, user=Depends(get_current_user)):
    q = await db.questions.find_one({"question_id": question_id}, {"_id": 0})
    if not q:
        return err("not_found", "Question not found", 404)
    return ok(q)

class AttemptIn(BaseModel):
    selected_answer: Any
    time_taken: int = 0

def _is_correct(qtype: str, correct: Any, selected: Any) -> bool:
    if qtype == "MCQ":
        return str(selected) == str(correct)
    if qtype == "MSQ":
        return sorted([str(x) for x in (selected or [])]) == sorted([str(x) for x in (correct or [])])
    if qtype == "NAT":
        try:
            return abs(float(selected) - float(correct)) < 1e-3
        except Exception:
            return False
    return False

@api.post("/questions/{question_id}/attempt")
async def attempt_question(question_id: str, body: AttemptIn, user=Depends(get_current_user)):
    q = await db.questions.find_one({"question_id": question_id}, {"_id": 0})
    if not q:
        return err("not_found", "Question not found", 404)
    correct = _is_correct(q["question_type"], q["correct_answer"], body.selected_answer)
    attempt = {
        "attempt_id": new_id("att"),
        "user_id": user["user_id"],
        "question_id": question_id,
        "selected_answer": body.selected_answer,
        "is_correct": correct,
        "time_taken": body.time_taken,
        "attempted_at": iso(now_utc()),
    }
    await db.question_attempts.insert_one(dict(attempt))
    attempt.pop("_id", None)
    return ok({"attempt": attempt, "correct_answer": q["correct_answer"], "solution": q["solution"]})

@api.get("/questions/{question_id}/attempts")
async def question_attempts(question_id: str, user=Depends(get_current_user)):
    docs = await db.question_attempts.find(
        {"user_id": user["user_id"], "question_id": question_id}, {"_id": 0}
    ).sort("attempted_at", -1).to_list(200)
    return ok(docs)

@api.get("/questions/{question_id}/notes")
async def get_question_notes(question_id: str, user=Depends(get_current_user)):
    n = await db.question_notes.find_one(
        {"user_id": user["user_id"], "question_id": question_id}, {"_id": 0}
    )
    return ok(n or {"note_content": "", "question_id": question_id})

class NotesIn(BaseModel):
    note_content: str

@api.post("/questions/{question_id}/notes")
async def save_question_notes(question_id: str, body: NotesIn, user=Depends(get_current_user)):
    await db.question_notes.update_one(
        {"user_id": user["user_id"], "question_id": question_id},
        {"$set": {"note_content": body.note_content, "updated_at": iso(now_utc())},
         "$setOnInsert": {"note_id": new_id("note"), "user_id": user["user_id"],
                          "question_id": question_id, "created_at": iso(now_utc())}},
        upsert=True,
    )
    return ok({"saved": True})

# ---------- PYQs ----------
@api.get("/pyqs")
async def list_pyqs(
    subject_id: Optional[str] = None, topic_id: Optional[str] = None,
    year: Optional[int] = None, limit: int = Query(50, le=200), skip: int = 0,
    user=Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if subject_id:
        q["subject_id"] = subject_id
    if topic_id:
        q["topic_id"] = topic_id
    if year:
        q["year"] = year
    total = await db.pyqs.count_documents(q)
    docs = await db.pyqs.find(q, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    pids = [d["pyq_id"] for d in docs]
    attempts = await db.pyq_attempts.find(
        {"user_id": user["user_id"], "pyq_id": {"$in": pids}}, {"_id": 0}
    ).to_list(2000)
    by_p: Dict[str, Dict[str, Any]] = {}
    for a in attempts:
        cur = by_p.setdefault(a["pyq_id"], {"count": 0, "correct": 0, "last_correct": None})
        cur["count"] += 1
        if a["is_correct"]:
            cur["correct"] += 1
        cur["last_correct"] = a["is_correct"]
    for d in docs:
        d["user_progress"] = by_p.get(d["pyq_id"], {"count": 0, "correct": 0, "last_correct": None})
    return ok({"items": docs, "total": total})

@api.get("/pyqs/{pyq_id}")
async def get_pyq(pyq_id: str, user=Depends(get_current_user)):
    q = await db.pyqs.find_one({"pyq_id": pyq_id}, {"_id": 0})
    if not q:
        return err("not_found", "PYQ not found", 404)
    return ok(q)

@api.post("/pyqs/{pyq_id}/attempt")
async def attempt_pyq(pyq_id: str, body: AttemptIn, user=Depends(get_current_user)):
    q = await db.pyqs.find_one({"pyq_id": pyq_id}, {"_id": 0})
    if not q:
        return err("not_found", "PYQ not found", 404)
    correct = _is_correct(q["question_type"], q["correct_answer"], body.selected_answer)
    attempt = {
        "attempt_id": new_id("patt"), "user_id": user["user_id"],
        "pyq_id": pyq_id, "selected_answer": body.selected_answer,
        "is_correct": correct, "time_taken": body.time_taken,
        "attempted_at": iso(now_utc()),
    }
    await db.pyq_attempts.insert_one(dict(attempt))
    attempt.pop("_id", None)
    return ok({"attempt": attempt, "correct_answer": q["correct_answer"], "solution": q["solution"]})

@api.get("/pyqs/{pyq_id}/attempts")
async def pyq_attempts_list(pyq_id: str, user=Depends(get_current_user)):
    docs = await db.pyq_attempts.find(
        {"user_id": user["user_id"], "pyq_id": pyq_id}, {"_id": 0}
    ).sort("attempted_at", -1).to_list(200)
    return ok(docs)

# ---------- Mistakes ----------
class MistakeIn(BaseModel):
    question_id: str
    mistake_type: str  # Conceptual Gap | Calculation Error | Question Misread | Silly Mistake
    note: Optional[str] = ""

@api.get("/mistakes")
async def list_mistakes(
    subject_id: Optional[str] = None, topic_id: Optional[str] = None,
    mistake_type: Optional[str] = None, user=Depends(get_current_user),
):
    q: Dict[str, Any] = {"user_id": user["user_id"]}
    if subject_id:
        q["subject_id"] = subject_id
    if topic_id:
        q["topic_id"] = topic_id
    if mistake_type:
        q["mistake_type"] = mistake_type
    docs = await db.mistakes.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for d in docs:
        q_doc = await db.questions.find_one({"question_id": d["question_id"]}, {"_id": 0})
        d["question"] = q_doc
    return ok(docs)

@api.post("/mistakes")
async def create_mistake(body: MistakeIn, user=Depends(get_current_user)):
    q = await db.questions.find_one({"question_id": body.question_id}, {"_id": 0})
    if not q:
        return err("not_found", "Question not found", 404)
    doc = {
        "mistake_id": new_id("mis"), "user_id": user["user_id"],
        "question_id": body.question_id, "subject_id": q["subject_id"],
        "topic_id": q["topic_id"], "mistake_type": body.mistake_type,
        "note": body.note or "", "created_at": iso(now_utc()),
    }
    await db.mistakes.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)

@api.delete("/mistakes/{mistake_id}")
async def delete_mistake(mistake_id: str, user=Depends(get_current_user)):
    r = await db.mistakes.delete_one({"mistake_id": mistake_id, "user_id": user["user_id"]})
    return ok({"deleted": r.deleted_count})

# ---------- Playlists / Videos ----------
def _extract_playlist_id(url: str) -> Optional[str]:
    m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None

def _iso8601_to_seconds(d: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "PT0S")
    if not m:
        return 0
    days, h, mi, s = m.groups()
    return (int(days or 0))*86400 + (int(h or 0))*3600 + (int(mi or 0))*60 + int(s or 0)

class PlaylistImportIn(BaseModel):
    youtube_url: str
    subject_id: str

YT_BASE = "https://www.googleapis.com/youtube/v3"


def _yt_fetch_playlist_meta(pid: str) -> Optional[Dict[str, Any]]:
    """Return playlist snippet + itemCount, or None if missing."""
    r = requests.get(
        f"{YT_BASE}/playlists",
        params={"part": "snippet,contentDetails", "id": pid, "key": YOUTUBE_API_KEY},
        timeout=15,
    ).json()
    items = r.get("items") or []
    if not items:
        return None
    return {
        "snippet": items[0]["snippet"],
        "item_count": items[0]["contentDetails"]["itemCount"],
    }


def _yt_fetch_playlist_items(pid: str) -> List[Dict[str, Any]]:
    """Return list of {youtube_video_id, title, position} for all videos in playlist."""
    videos: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    while True:
        params: Dict[str, Any] = {
            "part": "snippet,contentDetails", "playlistId": pid,
            "maxResults": 50, "key": YOUTUBE_API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token
        page = requests.get(f"{YT_BASE}/playlistItems", params=params, timeout=15).json()
        for it in page.get("items", []):
            videos.append({
                "youtube_video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "position": it["snippet"]["position"],
            })
        page_token = page.get("nextPageToken")
        if not page_token:
            return videos


def _yt_fetch_video_durations(video_ids: List[str]) -> Dict[str, int]:
    """Return mapping youtube_video_id → duration seconds."""
    out: Dict[str, int] = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        rv = requests.get(
            f"{YT_BASE}/videos",
            params={"part": "contentDetails", "id": ",".join(chunk), "key": YOUTUBE_API_KEY},
            timeout=15,
        ).json()
        for it in rv.get("items", []):
            out[it["id"]] = _iso8601_to_seconds(it["contentDetails"]["duration"])
    return out


def _build_playlist_doc(user_id: str, subject_id: str, pid: str,
                        meta: Dict[str, Any]) -> Dict[str, Any]:
    snip = meta["snippet"]
    thumbs = snip.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("default", {})).get("url", "")
    return {
        "playlist_id": new_id("pl"), "user_id": user_id, "subject_id": subject_id,
        "youtube_playlist_id": pid, "title": snip["title"], "thumbnail": thumb,
        "channel_title": snip.get("channelTitle", ""),
        "video_count": meta["item_count"], "created_at": iso(now_utc()),
    }


def _build_video_docs(playlist_id: str, videos: List[Dict[str, Any]],
                      durations: Dict[str, int]) -> List[Dict[str, Any]]:
    return [{
        "video_id": new_id("vid"), "playlist_id": playlist_id,
        "youtube_video_id": v["youtube_video_id"], "title": v["title"],
        "position": v["position"], "duration": durations.get(v["youtube_video_id"], 0),
    } for v in videos]


@api.post("/playlists/import")
async def import_playlist(body: PlaylistImportIn, user=Depends(get_current_user)):
    pid = _extract_playlist_id(body.youtube_url)
    if not pid:
        return err("invalid_url", "Invalid YouTube playlist URL", 400)
    if not YOUTUBE_API_KEY:
        return err("config", "YOUTUBE_API_KEY not configured", 500)
    existing = await db.playlists.find_one(
        {"user_id": user["user_id"], "youtube_playlist_id": pid}, {"_id": 0}
    )
    if existing:
        return ok(existing)
    try:
        meta = _yt_fetch_playlist_meta(pid)
        if not meta:
            return err("not_found", "Playlist not found on YouTube", 404)
        videos = _yt_fetch_playlist_items(pid)
        durations = _yt_fetch_video_durations([v["youtube_video_id"] for v in videos])
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

@api.get("/playlists")
async def my_playlists(subject_id: Optional[str] = None, user=Depends(get_current_user)):
    q: Dict[str, Any] = {"user_id": user["user_id"]}
    if subject_id:
        q["subject_id"] = subject_id
    docs = await db.playlists.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    # progress: completed videos count
    for d in docs:
        vids = await db.videos.find({"playlist_id": d["playlist_id"]}, {"_id": 0, "video_id": 1}).to_list(1000)
        vid_ids = [v["video_id"] for v in vids]
        completed = await db.video_progress.count_documents({
            "user_id": user["user_id"], "video_id": {"$in": vid_ids}, "completed": True
        })
        d["completed_videos"] = completed
    return ok(docs)

@api.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: str, user=Depends(get_current_user)):
    p = await db.playlists.find_one({"playlist_id": playlist_id, "user_id": user["user_id"]}, {"_id": 0})
    if not p:
        return err("not_found", "Playlist not found", 404)
    videos = await db.videos.find({"playlist_id": playlist_id}, {"_id": 0}).sort("position", 1).to_list(2000)
    vid_ids = [v["video_id"] for v in videos]
    prog = await db.video_progress.find(
        {"user_id": user["user_id"], "video_id": {"$in": vid_ids}}, {"_id": 0}
    ).to_list(2000)
    pmap = {x["video_id"]: x for x in prog}
    for v in videos:
        v["progress"] = pmap.get(v["video_id"], {"watch_percentage": 0, "completed": False, "watch_time": 0})
    p["videos"] = videos
    return ok(p)

@api.delete("/playlists/{playlist_id}")
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

class VideoProgressIn(BaseModel):
    watch_percentage: float
    watch_time: int = 0

@api.post("/videos/{video_id}/progress")
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

# ---------- Resources ----------
class ResourceIn(BaseModel):
    subject_id: str
    resource_type: str  # Books, Notes, Question Banks, PYQ Collections, Formula Sheets, Reference Material
    title: str
    external_url: Optional[str] = ""  # link to Google Drive / Dropbox / etc.
    file_size: Optional[int] = 0

@api.post("/resources")
async def create_resource(body: ResourceIn, user=Depends(get_current_user)):
    doc = {
        "resource_id": new_id("res"), "user_id": user["user_id"],
        "subject_id": body.subject_id, "resource_type": body.resource_type,
        "title": body.title, "external_url": body.external_url or "",
        "file_size": body.file_size or 0, "created_at": iso(now_utc()),
    }
    await db.resources.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)

@api.get("/resources")
async def list_resources(subject_id: Optional[str] = None, resource_type: Optional[str] = None,
                        user=Depends(get_current_user)):
    q: Dict[str, Any] = {"user_id": user["user_id"]}
    if subject_id:
        q["subject_id"] = subject_id
    if resource_type:
        q["resource_type"] = resource_type
    docs = await db.resources.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return ok(docs)

@api.delete("/resources/{resource_id}")
async def delete_resource(resource_id: str, user=Depends(get_current_user)):
    r = await db.resources.delete_one({"resource_id": resource_id, "user_id": user["user_id"]})
    return ok({"deleted": r.deleted_count})

# ---------- Dashboard / Analytics ----------
def _accuracy(attempts: List[Dict[str, Any]]) -> float:
    if not attempts:
        return 0.0
    correct = sum(1 for a in attempts if a["is_correct"])
    return round(correct / len(attempts) * 100, 1)


def _progress_bucket(attempts: List[Dict[str, Any]], total: int, key: str) -> Dict[str, Any]:
    solved = len({a[key] for a in attempts})
    return {
        "total": total, "solved": solved, "remaining": total - solved,
        "accuracy": _accuracy(attempts),
    }


def _overall_summary(qa: List[Dict[str, Any]], pa: List[Dict[str, Any]],
                    counts: Dict[str, int]) -> Dict[str, Any]:
    return {
        "questions_solved": len({a["question_id"] for a in qa}),
        "pyqs_solved": len({a["pyq_id"] for a in pa}),
        "videos_completed": counts["videos_done"],
        "total_playlists": counts["playlists"],
        "question_accuracy": _accuracy(qa),
        "pyq_accuracy": _accuracy(pa),
        "total_mistakes": counts["mistakes"],
        "resources_uploaded": counts["resources"],
    }


async def _subject_overview_row(subject: Dict[str, Any],
                                qa: List[Dict[str, Any]],
                                pa: List[Dict[str, Any]]) -> Dict[str, Any]:
    sid = subject["subject_id"]
    qb_total = await db.questions.count_documents({"subject_id": sid})
    pyq_total = await db.pyqs.count_documents({"subject_id": sid})
    qids = {q["question_id"] async for q in db.questions.find(
        {"subject_id": sid}, {"_id": 0, "question_id": 1})}
    pids = {p["pyq_id"] async for p in db.pyqs.find(
        {"subject_id": sid}, {"_id": 0, "pyq_id": 1})}
    ua = [a for a in qa if a["question_id"] in qids]
    upa = [a for a in pa if a["pyq_id"] in pids]
    return {
        "subject": subject,
        "qb": _progress_bucket(ua, qb_total, "question_id"),
        "pyq": _progress_bucket(upa, pyq_total, "pyq_id"),
    }


def _recent_activity(qa: List[Dict[str, Any]], pa: List[Dict[str, Any]],
                     limit: int = 10) -> List[Dict[str, Any]]:
    merged = (
        [{"type": "question", **a} for a in qa[-5:]] +
        [{"type": "pyq", **a} for a in pa[-5:]]
    )
    return sorted(merged, key=lambda x: x["attempted_at"], reverse=True)[:limit]


@api.get("/dashboard")
async def dashboard(user=Depends(get_current_user)) -> Dict[str, Any]:
    uid = user["user_id"]
    qa = await db.question_attempts.find({"user_id": uid}, {"_id": 0}).to_list(20000)
    pa = await db.pyq_attempts.find({"user_id": uid}, {"_id": 0}).to_list(20000)
    counts = {
        "playlists": await db.playlists.count_documents({"user_id": uid}),
        "videos_done": await db.video_progress.count_documents({"user_id": uid, "completed": True}),
        "mistakes": await db.mistakes.count_documents({"user_id": uid}),
        "resources": await db.resources.count_documents({"user_id": uid}),
    }
    subjects = await db.subjects.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    overview = [await _subject_overview_row(s, qa, pa) for s in subjects]
    return ok({
        "summary": _overall_summary(qa, pa, counts),
        "subjects": overview,
        "recent_activity": _recent_activity(qa, pa),
    })


async def _topic_progress_row(topic: Dict[str, Any], uid: str,
                              qa: List[Dict[str, Any]],
                              pa: List[Dict[str, Any]]) -> Dict[str, Any]:
    tid = topic["topic_id"]
    qids = [q["question_id"] async for q in db.questions.find(
        {"topic_id": tid}, {"_id": 0, "question_id": 1})]
    pids = [p["pyq_id"] async for p in db.pyqs.find(
        {"topic_id": tid}, {"_id": 0, "pyq_id": 1})]
    ua = [a for a in qa if a["question_id"] in qids]
    upa = [a for a in pa if a["pyq_id"] in pids]
    notes = await db.question_notes.count_documents({"user_id": uid, "question_id": {"$in": qids}})
    mis = await db.mistakes.count_documents({"user_id": uid, "topic_id": tid})
    return {
        "topic": topic,
        "qb": _progress_bucket(ua, len(qids), "question_id"),
        "pyq": _progress_bucket(upa, len(pids), "pyq_id"),
        "notes_count": notes,
        "mistakes_count": mis,
    }


@api.get("/analytics/subject/{subject_id}")
async def subject_analytics(subject_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    uid = user["user_id"]
    topics = await db.topics.find({"subject_id": subject_id}, {"_id": 0}).sort("order", 1).to_list(200)
    qa = await db.question_attempts.find({"user_id": uid}, {"_id": 0}).to_list(20000)
    pa = await db.pyq_attempts.find({"user_id": uid}, {"_id": 0}).to_list(20000)
    rows = [await _topic_progress_row(t, uid, qa, pa) for t in topics]
    return ok(rows)


@api.get("/analytics/topic/{topic_id}")
async def topic_analytics(topic_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    uid = user["user_id"]
    t = await db.topics.find_one({"topic_id": topic_id}, {"_id": 0})
    if not t:
        return err("not_found", "Topic not found", 404)
    qa = await db.question_attempts.find({"user_id": uid}, {"_id": 0}).to_list(20000)
    pa = await db.pyq_attempts.find({"user_id": uid}, {"_id": 0}).to_list(20000)
    return ok(await _topic_progress_row(t, uid, qa, pa))

# ---------- Admin ----------
class QuestionIn(BaseModel):
    subject_id: str
    topic_id: str
    question_type: str  # MCQ | MSQ | NAT
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: Any
    solution: str
    difficulty: str = "Medium"
    source: str = "Admin"
    year: Optional[int] = None

@api.post("/admin/questions")
async def admin_create_question(body: QuestionIn, user=Depends(require_admin)):
    doc = {"question_id": new_id("q"), **body.model_dump(), "created_at": iso(now_utc())}
    await db.questions.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)

@api.delete("/admin/questions/{question_id}")
async def admin_delete_question(question_id: str, user=Depends(require_admin)):
    r = await db.questions.delete_one({"question_id": question_id})
    return ok({"deleted": r.deleted_count})

class PYQIn(QuestionIn):
    year: int

@api.post("/admin/pyqs")
async def admin_create_pyq(body: PYQIn, user=Depends(require_admin)):
    doc = {"pyq_id": new_id("pyq"), **body.model_dump(), "created_at": iso(now_utc())}
    await db.pyqs.insert_one(dict(doc))
    doc.pop("_id", None)
    return ok(doc)

@api.delete("/admin/pyqs/{pyq_id}")
async def admin_delete_pyq(pyq_id: str, user=Depends(require_admin)):
    r = await db.pyqs.delete_one({"pyq_id": pyq_id})
    return ok({"deleted": r.deleted_count})

@api.get("/admin/users")
async def admin_users(user=Depends(require_admin)):
    docs = await db.users.find({}, {"_id": 0}).to_list(10000)
    return ok(docs)

# ---------- Seed ----------
SUBJECTS_SEED = [
    ("Engineering Mathematics", ["Discrete Mathematics", "Linear Algebra", "Calculus", "Probability & Statistics"]),
    ("Digital Logic", ["Number Systems", "Boolean Algebra", "Combinational Circuits", "Sequential Circuits", "Minimization"]),
    ("Computer Organization and Architecture", ["Machine Instructions", "ALU & Datapath", "Pipelining", "Memory Hierarchy", "I/O Interface"]),
    ("Programming and Data Structures", ["C Programming", "Arrays & Strings", "Linked Lists", "Stacks & Queues", "Trees", "Graphs", "Hashing"]),
    ("Algorithms", ["Asymptotic Analysis", "Searching & Sorting", "Greedy", "Divide & Conquer", "Dynamic Programming", "Graph Algorithms"]),
    ("Theory of Computation", ["Regular Languages", "Context-Free Languages", "Pushdown Automata", "Turing Machines", "Undecidability"]),
    ("Compiler Design", ["Lexical Analysis", "Parsing", "Syntax-Directed Translation", "Intermediate Code", "Code Optimization"]),
    ("Operating Systems", ["Processes & Threads", "CPU Scheduling", "Synchronization", "Deadlocks", "Memory Management", "File Systems"]),
    ("Databases", ["ER Model", "Relational Algebra", "SQL", "Normalization", "Transactions & Concurrency", "Indexing"]),
    ("Computer Networks", ["OSI & TCP/IP", "Physical Layer", "Data Link Layer", "Network Layer", "Transport Layer", "Application Layer"]),
]

SAMPLE_QUESTIONS = [
    {"subject": "Operating Systems", "topic": "CPU Scheduling", "qt": "MCQ",
     "qtext": "Which scheduling algorithm allocates CPU to the process with the smallest CPU burst time?",
     "opts": ["FCFS", "SJF", "Round Robin", "Priority"], "ans": "1",
     "sol": "Shortest Job First (SJF) selects the process with the smallest next CPU burst, minimizing average waiting time.",
     "diff": "Easy"},
    {"subject": "Operating Systems", "topic": "Synchronization", "qt": "MSQ",
     "qtext": "Which of the following are valid solutions to the critical section problem?",
     "opts": ["Peterson's algorithm", "Test-and-Set", "Disabling interrupts (uniprocessor)", "Busy waiting only"],
     "ans": ["0", "1", "2"],
     "sol": "Peterson's, TAS, and disabling interrupts on uniprocessors are valid; busy waiting alone is not sufficient.",
     "diff": "Medium"},
    {"subject": "Operating Systems", "topic": "Memory Management", "qt": "NAT",
     "qtext": "A system uses 32-bit addresses with 4 KB pages. How many bits are used for the page offset?",
     "opts": None, "ans": "12",
     "sol": "Page size = 4096 = 2^12, so offset = 12 bits.",
     "diff": "Easy"},
    {"subject": "Algorithms", "topic": "Asymptotic Analysis", "qt": "MCQ",
     "qtext": "What is the time complexity of binary search on a sorted array of n elements?",
     "opts": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "ans": "1",
     "sol": "Binary search halves the search space each iteration → O(log n).",
     "diff": "Easy"},
    {"subject": "Algorithms", "topic": "Dynamic Programming", "qt": "MCQ",
     "qtext": "Which is NOT a property required for a problem to be solvable by DP?",
     "opts": ["Optimal substructure", "Overlapping subproblems", "Greedy choice", "Recursive formulation"],
     "ans": "2",
     "sol": "Greedy choice is required for greedy algorithms, not DP.",
     "diff": "Medium"},
    {"subject": "Databases", "topic": "Normalization", "qt": "MCQ",
     "qtext": "A relation in 3NF is automatically in:",
     "opts": ["1NF only", "2NF only", "1NF and 2NF", "BCNF"], "ans": "2",
     "sol": "3NF requires the relation to satisfy 1NF and 2NF first.",
     "diff": "Easy"},
    {"subject": "Databases", "topic": "SQL", "qt": "NAT",
     "qtext": "How many rows are returned by SELECT COUNT(*) FROM R where R has 100 rows and no WHERE clause?",
     "opts": None, "ans": "1",
     "sol": "COUNT(*) without GROUP BY returns a single row containing the count.",
     "diff": "Easy"},
    {"subject": "Computer Networks", "topic": "Transport Layer", "qt": "MCQ",
     "qtext": "Which protocol provides reliable, connection-oriented service?",
     "opts": ["UDP", "TCP", "IP", "ICMP"], "ans": "1",
     "sol": "TCP is connection-oriented and provides reliable delivery via acknowledgments.",
     "diff": "Easy"},
    {"subject": "Theory of Computation", "topic": "Regular Languages", "qt": "MCQ",
     "qtext": "Which of the following languages is NOT regular?",
     "opts": ["{a^n b^m | n,m ≥ 0}", "{a^n b^n | n ≥ 0}", "Strings ending in 'ab'", "Even-length strings over {a,b}"],
     "ans": "1",
     "sol": "{a^n b^n} requires counting and is not regular (provable by pumping lemma).",
     "diff": "Medium"},
    {"subject": "Programming and Data Structures", "topic": "Trees", "qt": "NAT",
     "qtext": "What is the maximum number of nodes in a binary tree of height 3? (Root at height 0)",
     "opts": None, "ans": "15",
     "sol": "Maximum nodes in a binary tree of height h = 2^(h+1) - 1 = 2^4 - 1 = 15.",
     "diff": "Medium"},
    {"subject": "Digital Logic", "topic": "Boolean Algebra", "qt": "MCQ",
     "qtext": "A.(A+B) simplifies to:",
     "opts": ["A", "B", "A+B", "AB"], "ans": "0",
     "sol": "Absorption law: A.(A+B) = A.",
     "diff": "Easy"},
    {"subject": "Compiler Design", "topic": "Parsing", "qt": "MCQ",
     "qtext": "Which parser is most powerful?",
     "opts": ["LL(1)", "SLR", "LALR", "Canonical LR"], "ans": "3",
     "sol": "Canonical LR (CLR) handles the largest class of grammars among these.",
     "diff": "Medium"},
]

SAMPLE_PYQS = [
    {"subject": "Operating Systems", "topic": "Deadlocks", "year": 2023, "qt": "MCQ",
     "qtext": "Banker's algorithm is used for:",
     "opts": ["Deadlock prevention", "Deadlock avoidance", "Deadlock detection", "Deadlock recovery"],
     "ans": "1", "sol": "Banker's algorithm is a deadlock avoidance algorithm.", "diff": "Medium"},
    {"subject": "Algorithms", "topic": "Graph Algorithms", "year": 2022, "qt": "MCQ",
     "qtext": "Dijkstra's algorithm fails when the graph contains:",
     "opts": ["Cycles", "Negative weight edges", "Disconnected components", "Self loops"],
     "ans": "1", "sol": "Dijkstra assumes non-negative edge weights.", "diff": "Medium"},
    {"subject": "Databases", "topic": "Transactions & Concurrency", "year": 2021, "qt": "MCQ",
     "qtext": "Two-phase locking guarantees:",
     "opts": ["No deadlocks", "Serializability", "Recoverability", "Avoidance of starvation"],
     "ans": "1", "sol": "2PL ensures conflict-serializable schedules.", "diff": "Medium"},
    {"subject": "Computer Networks", "topic": "Network Layer", "year": 2023, "qt": "NAT",
     "qtext": "How many host bits in a /24 IPv4 network?",
     "opts": None, "ans": "8", "sol": "32 - 24 = 8 host bits.", "diff": "Easy"},
    {"subject": "Theory of Computation", "topic": "Turing Machines", "year": 2020, "qt": "MCQ",
     "qtext": "Which problem is undecidable?",
     "opts": ["Membership in regular language", "Emptiness of regular language",
              "Halting problem", "Equivalence of DFAs"],
     "ans": "2", "sol": "Halting problem is the classic undecidable problem (Turing 1936).", "diff": "Hard"},
    {"subject": "Programming and Data Structures", "topic": "Hashing", "year": 2022, "qt": "MCQ",
     "qtext": "Open addressing with linear probing suffers most from:",
     "opts": ["Secondary clustering", "Primary clustering", "Chaining overhead", "Hash collisions only"],
     "ans": "1", "sol": "Linear probing causes primary clustering.", "diff": "Medium"},
]

async def _seed_subjects_and_topics() -> None:
    if await db.subjects.count_documents({}) > 0:
        return
    for i, (name, topics) in enumerate(SUBJECTS_SEED):
        sid = new_id("sub")
        await db.subjects.insert_one({
            "subject_id": sid, "name": name, "order": i,
            "created_at": iso(now_utc()),
        })
        topic_docs = [{
            "topic_id": new_id("top"), "subject_id": sid, "name": tname,
            "order": j, "created_at": iso(now_utc()),
        } for j, tname in enumerate(topics)]
        if topic_docs:
            await db.topics.insert_many(topic_docs)


async def _name_id_maps() -> tuple:
    """Build (subjects-by-name, topics-by-(subject_id,name)) maps."""
    subs = {s["name"]: s async for s in db.subjects.find({}, {"_id": 0})}
    tops = {(t["subject_id"], t["name"]): t
            async for t in db.topics.find({}, {"_id": 0})}
    return subs, tops


async def _seed_questions(subs: Dict[str, Any], tops: Dict[tuple, Any]) -> None:
    if await db.questions.count_documents({}) > 0:
        return
    for q in SAMPLE_QUESTIONS:
        s = subs.get(q["subject"])
        if not s:
            continue
        t = tops.get((s["subject_id"], q["topic"]))
        if not t:
            continue
        await db.questions.insert_one({
            "question_id": new_id("q"), "subject_id": s["subject_id"],
            "topic_id": t["topic_id"], "question_type": q["qt"],
            "question_text": q["qtext"], "options": q["opts"],
            "correct_answer": q["ans"], "solution": q["sol"],
            "difficulty": q["diff"], "source": "Seed Pack",
            "created_at": iso(now_utc()),
        })


async def _seed_pyqs(subs: Dict[str, Any], tops: Dict[tuple, Any]) -> None:
    if await db.pyqs.count_documents({}) > 0:
        return
    for p in SAMPLE_PYQS:
        s = subs.get(p["subject"])
        if not s:
            continue
        t = tops.get((s["subject_id"], p["topic"]))
        if not t:
            continue
        await db.pyqs.insert_one({
            "pyq_id": new_id("pyq"), "subject_id": s["subject_id"],
            "topic_id": t["topic_id"], "year": p["year"],
            "question_type": p["qt"], "question_text": p["qtext"],
            "options": p["opts"], "correct_answer": p["ans"],
            "solution": p["sol"], "difficulty": p["diff"],
            "source": f"GATE {p['year']}", "created_at": iso(now_utc()),
        })


@api.post("/seed")
async def seed_data() -> Dict[str, Any]:
    """Idempotent seed of subjects, topics, sample questions, sample PYQs."""
    await _seed_subjects_and_topics()
    subs, tops = await _name_id_maps()
    await _seed_questions(subs, tops)
    await _seed_pyqs(subs, tops)
    return ok({
        "subjects": await db.subjects.count_documents({}),
        "topics": await db.topics.count_documents({}),
        "questions": await db.questions.count_documents({}),
        "pyqs": await db.pyqs.count_documents({}),
    })

@api.get("/")
async def root():
    return {"service": "gate-study-os", "version": "1.0"}

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    # auto-seed at startup
    try:
        if await db.subjects.count_documents({}) == 0:
            await seed_data()
            logger.info("Seeded GATE syllabus")
    except Exception as e:
        logger.error(f"Seed error: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    client.close()
