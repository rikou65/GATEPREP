from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.providers import (
    get_playlist_commands,
    get_playlist_queries,
)
from app.api.responses import err, ok
from app.schemas.auth import CurrentUser
from app.schemas.common import Envelope, ProgressOut, VideoNotesOut, VideoSavedOut
from app.schemas.playlists import PlaylistImportIn, VideoNotesIn, VideoProgressIn
from app.services.playlists.commands import PlaylistCommands
from app.services.playlists.queries import PlaylistQueries

router = APIRouter()


@router.post("/playlists/import", response_model=Envelope[dict])
async def import_playlist(
    body: PlaylistImportIn,
    user: CurrentUser = Depends(get_current_user),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    result = await commands.import_from_youtube_url(
        user.user_id, body.youtube_url, body.subject_id
    )
    if isinstance(result, dict) and "error" in result:
        return err(
            result["error"],
            result.get("message", "Unknown YouTube error"),
            result.get("status_code", 502),
        )
    return ok(result)


@router.get("/playlists", response_model=Envelope[List[dict]])
async def my_playlists(
    subject_id: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    queries: PlaylistQueries = Depends(get_playlist_queries),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    async def refresh_cb(uid, pids):
        await commands.refresh_missing_durations(uid, pids)

    docs = await queries.list_playlists(user.user_id, subject_id, refresh_cb)
    return ok(docs)


@router.get("/playlists/{playlist_id}", response_model=Envelope[dict])
async def get_playlist(
    playlist_id: str,
    user: CurrentUser = Depends(get_current_user),
    queries: PlaylistQueries = Depends(get_playlist_queries),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    async def refresh_cb(uid, pids):
        await commands.refresh_missing_durations(uid, pids)

    result = await queries.get_playlist(user.user_id, playlist_id, refresh_cb)
    if result is None:
        return err("not_found", "Playlist not found", 404)
    return ok(result)


@router.delete("/playlists/{playlist_id}", response_model=Envelope[dict])
async def delete_playlist(
    playlist_id: str,
    user: CurrentUser = Depends(get_current_user),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    deleted = await commands.delete_playlist(user.user_id, playlist_id)
    if not deleted:
        return err("not_found", "Not found", 404)
    return ok({"deleted": True})


@router.post("/videos/{video_id}/progress", response_model=Envelope[ProgressOut])
async def update_video_progress(
    video_id: str,
    body: VideoProgressIn,
    user: CurrentUser = Depends(get_current_user),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    result = await commands.update_progress(
        user.user_id,
        video_id,
        body.watch_percentage,
        body.watch_time,
        body.completed,
    )
    if result is None:
        return err("not_found", "Not found", 404)
    return ok(result)


@router.get("/videos/{video_id}/notes", response_model=Envelope[VideoNotesOut])
async def get_video_notes(
    video_id: str,
    user: CurrentUser = Depends(get_current_user),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    notes = await commands.get_video_notes(user.user_id, video_id)
    if notes is None:
        return err("not_found", "Not found", 404)
    return ok(notes)


@router.post("/videos/{video_id}/notes", response_model=Envelope[VideoSavedOut])
async def save_video_notes(
    video_id: str,
    body: VideoNotesIn,
    user: CurrentUser = Depends(get_current_user),
    commands: PlaylistCommands = Depends(get_playlist_commands),
):
    result = await commands.save_video_notes(
        user.user_id, video_id, body.note_content
    )
    if result is None:
        return err("not_found", "Not found", 404)
    return ok(result)
