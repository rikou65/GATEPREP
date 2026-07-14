from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    success: bool = True
    data: T


class ErrorPayload(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorPayload


class OutModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class DeletedOut(OutModel):
    deleted: int


class SavedOut(OutModel):
    saved: bool


class ApprovedOut(OutModel):
    approved: int


class BulkApprovedOut(OutModel):
    approved: int
    questions_added: int
    pyqs_added: int


class JobCreatedOut(OutModel):
    job_id: str


class DismissedOut(OutModel):
    dismissed: int


class DisconnectedOut(OutModel):
    disconnected: bool


class LoggedOut(OutModel):
    logged_out: bool


class GoogleUrlOut(OutModel):
    authorization_url: str


class DriveStatusOut(OutModel):
    connected: bool
    user_id: Optional[str] = None
    drive_email: Optional[str] = None
    connected_at: Optional[str] = None


class YouTubeStatusOut(OutModel):
    connected: bool
    connected_at: Optional[str] = None


class RefreshedOut(OutModel):
    refreshed: bool
    valid: bool


class SyncedOut(OutModel):
    synced: int
    skipped: int
    unknown_subjects: List[str] = []


class ProgressOut(OutModel):
    watch_percentage: float
    completed: bool


class VideoSavedOut(OutModel):
    saved: bool


class QuestionNotesOut(OutModel):
    note_content: str = ""
    question_id: str


class VideoNotesOut(OutModel):
    note_content: str = ""
    video_id: str


class FlagsOut(OutModel):
    flags: List[str]


class ResourceViewOut(OutModel):
    embed_url: str
    view_url: str
    kind: str


class TogglePageOut(OutModel):
    important_pages: List[dict] = []
    action: str
    page: int


class LabelPageOut(OutModel):
    important_pages: List[dict] = []
    page: int
    label: str


class ImportResultOut(OutModel):
    already_exists: Optional[bool] = None
    playlist_id: Optional[str] = None
    youtube_playlist_id: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    channel_title: Optional[str] = None
    video_count: Optional[int] = None
    created_at: Optional[str] = None
    subject_id: Optional[str] = None
    user_id: Optional[str] = None
    error: Optional[str] = None