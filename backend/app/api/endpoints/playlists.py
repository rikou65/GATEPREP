from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.responses import err, ok
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
from app.schemas.playlists import PlaylistImportIn, VideoNotesIn, VideoProgressIn
from app.services.playlists.commands import PlaylistCommands, extract_playlist_id
from app.services.playlists.queries import PlaylistQueries

router = APIRouter()


def _build_services(request: Request):
    db = request.app.state.db
    pl_repo = PlaylistRepository(db)
    vid_repo = VideoRepository(db)
    prog_repo = VideoProgressRepository(db)
    note_repo = VideoNoteRepository(db)
    commands = PlaylistCommands(pl_repo, vid_repo, prog_repo, note_repo)
    queries = PlaylistQueries(pl_repo, vid_repo, prog_repo)
    return pl_repo, vid_repo, prog_repo, note_repo, commands, queries


async def _get_youtube_token(user_id: str, request: Request) -> Optional[str]:
    settings = request.app.state.settings
    manager = YouTubeTokenManager(
        settings.GOOGLE_DRIVE_CLIENT_ID,
        settings.GOOGLE_DRIVE_CLIENT_SECRET,
        settings.GOOGLE_YOUTUBE_REDIRECT_URI,
    )
    repo = YouTubeCredentialRepository(request.app.state.db)
    return await manager.get_token(user_id, repo)


async def _refresh_missing_durations(
    user_id: str,
    playlist_ids: list[str],
    vid_repo: VideoRepository,
    request: Request,
) -> None:
    token = await _get_youtube_token(user_id, request)
    if not token:
        return
    yt_api = YouTubeAPI(request.app.state.settings.YOUTUBE_API_KEY)
    for playlist_id in playlist_ids:
        videos = await vid_repo.find_with_zero_duration(playlist_id)
        if not videos:
            continue
        youtube_ids = [v["youtube_video_id"] for v in videos]
        try:
            durations = await yt_api.fetch_video_durations(youtube_ids, token)
        except Exception:
            continue
        for youtube_id, duration in durations.items():
            if duration > 0:
                await vid_repo.update_duration(
                    playlist_id, youtube_id, duration
                )


@router.post("/playlists/import")
async def import_playlist(
    body: PlaylistImportIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, commands, _ = _build_services(request)
    if not extract_playlist_id(body.youtube_url):
        return err("invalid_url", "Invalid YouTube playlist URL", 400)
    yt_token = await _get_youtube_token(user["user_id"], request)
    if not yt_token:
        return err(
            "youtube_not_connected",
            "Connect YouTube in Settings first",
            400,
        )
    yt_api = YouTubeAPI(request.app.state.settings.YOUTUBE_API_KEY)
    try:
        result = await commands.import_playlist(
            user["user_id"],
            body.youtube_url,
            body.subject_id,
            yt_token,
            yt_api,
        )
    except YouTubeAPIError as exc:
        if exc.clear_credentials:
            await YouTubeCredentialRepository(request.app.state.db).delete(user["user_id"])
        return err(exc.code, exc.message, exc.status_code)
    if result is None:
        return err("invalid_url", "Invalid YouTube playlist URL", 400)
    if isinstance(result, dict) and "error" in result:
        err_map = {
            "youtube_not_connected": (
                "youtube_not_connected",
                "Connect YouTube in Settings first",
                400,
            ),
            "not_found": ("not_found", "Playlist not found on YouTube", 404),
        }
        e = err_map.get(
            result["error"], ("youtube_error", result.get("msg", "Unknown error"), 502)
        )
        return err(*e)
    return ok(result)


@router.get("/playlists")
async def my_playlists(
    request: Request,
    subject_id: Optional[str] = None,
    user=Depends(get_current_user),
):
    _, vid_repo, _, _, _, queries = _build_services(request)

    async def refresh_cb(uid, pids):
        await _refresh_missing_durations(uid, pids, vid_repo, request)

    docs = await queries.list_playlists(
        user["user_id"], subject_id, refresh_cb
    )
    return ok(docs)


@router.get("/playlists/{playlist_id}")
async def get_playlist(
    playlist_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, vid_repo, _, _, _, queries = _build_services(request)

    async def refresh_cb(uid, pids):
        await _refresh_missing_durations(uid, pids, vid_repo, request)

    result = await queries.get_playlist(
        user["user_id"], playlist_id, refresh_cb
    )
    if result is None:
        return err("not_found", "Playlist not found", 404)
    return ok(result)


@router.delete("/playlists/{playlist_id}")
async def delete_playlist(
    playlist_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, _, commands, _ = _build_services(request)
    deleted = await commands.delete_playlist(
        user["user_id"], playlist_id
    )
    if not deleted:
        return err("not_found", "Not found", 404)
    return ok({"deleted": True})


@router.post("/videos/{video_id}/progress")
async def update_video_progress(
    video_id: str,
    body: VideoProgressIn,
    request: Request,
    user=Depends(get_current_user),
):
    pl_repo, vid_repo, prog_repo, _, _, _ = _build_services(request)

    v = await vid_repo.find_by_id(video_id)
    if not v:
        return err("not_found", "Not found", 404)
    if not await pl_repo.owns_playlist(user["user_id"], v["playlist_id"]):
        return err("not_found", "Not found", 404)

    if body.completed is not None:
        completed = body.completed
    else:
        existing = await prog_repo.find(
            user["user_id"], video_id, {"completed": 1}
        )
        if existing and existing.get("completed") is True:
            completed = True
        else:
            completed = body.watch_percentage >= 90

    await prog_repo.upsert(
        user["user_id"],
        video_id,
        {
            "watch_percentage": body.watch_percentage,
            "completed": completed,
            "watch_time": body.watch_time,
        },
    )
    return ok(
        {"watch_percentage": body.watch_percentage, "completed": completed}
    )


@router.get("/videos/{video_id}/notes")
async def get_video_notes(
    video_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    pl_repo, vid_repo, _, note_repo, _, _ = _build_services(request)

    v = await vid_repo.find_by_id(video_id)
    if not v:
        return err("not_found", "Not found", 404)
    if not await pl_repo.owns_playlist(user["user_id"], v["playlist_id"]):
        return err("not_found", "Not found", 404)

    n = await note_repo.find(user["user_id"], video_id)
    return ok(
        n or {"note_content": "", "video_id": video_id}
    )


@router.post("/videos/{video_id}/notes")
async def save_video_notes(
    video_id: str,
    body: VideoNotesIn,
    request: Request,
    user=Depends(get_current_user),
):
    pl_repo, vid_repo, _, note_repo, _, _ = _build_services(request)

    v = await vid_repo.find_by_id(video_id)
    if not v:
        return err("not_found", "Not found", 404)
    if not await pl_repo.owns_playlist(user["user_id"], v["playlist_id"]):
        return err("not_found", "Not found", 404)

    await note_repo.upsert(user["user_id"], video_id, body.note_content)
    return ok({"saved": True})
