from __future__ import annotations

from typing import Any

from fastapi import Depends, Request

from app.core.config import Settings
from app.integrations.google_drive import GoogleDriveIntegration
from app.integrations.google_oauth import GoogleOAuthIntegration
from app.integrations.google_youtube import YouTubeAPI, YouTubeTokenManager
from app.integrations.supabase_auth import SupabaseAuthIntegration
from app.repositories.analytics import AnalyticsRepository
from app.repositories.migration import MigrationRepository
from app.repositories.mistakes import MistakeRepository
from app.repositories.oauth_states import OAuthStateRepository
from app.repositories.playlists import (
    PlaylistRepository,
    VideoNoteRepository,
    VideoProgressRepository,
    VideoRepository,
)
from app.repositories.pyqs import PYQAttemptRepository, PYQRepository
from app.repositories.questions import (
    QuestionAttemptRepository,
    QuestionNoteRepository,
    QuestionRepository,
)
from app.repositories.resources import (
    DriveCredentialRepository,
    ResourceNoteRepository,
    ResourceRepository,
)
from app.repositories.search import SearchRepository
from app.repositories.sessions import SessionRepository
from app.repositories.staging import (
    ImportedQuestionRepository,
    ImportJobRepository,
    StagingQuestionRepository,
)
from app.repositories.subjects import SubjectRepository
from app.repositories.users import UserRepository
from app.repositories.youtube import YouTubeCredentialRepository
from app.services.analytics import AnalyticsService
from app.services.auth.identity_repair_service import IdentityRepairService
from app.services.auth.oauth_state_service import OAuthStateService
from app.services.auth.session_service import SessionService
from app.services.auth.supabase_service import SupabaseAuthService
from app.services.auth.user_service import UserService
from app.services.playlists.commands import PlaylistCommands
from app.services.playlists.queries import PlaylistQueries
from app.services.practice import (
    MistakeService,
    PYQAttemptService,
    PYQService,
    QuestionAttemptService,
    QuestionFlagService,
    QuestionNoteService,
    QuestionService,
)
from app.services.resources import ResourceService
from app.services.search import SearchService
from app.services.staging import StagingService
from app.services.subjects import SubjectService
from app.services.youtube import YouTubeService

# ── DB / Settings ──────────────────────────────────────────────────────────


def get_db(request: Request) -> Any:
    return request.app.state.db


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


# ── Singletons (cached on app.state) ───────────────────────────────────────


def get_drive_integration(request: Request) -> GoogleDriveIntegration:
    drive: GoogleDriveIntegration | None = getattr(
        request.app.state, "drive_integration", None
    )
    if drive is None:
        settings = get_settings(request)
        drive = GoogleDriveIntegration(settings)
        request.app.state.drive_integration = drive
    return drive


def get_youtube_token_manager(request: Request) -> YouTubeTokenManager:
    tm: YouTubeTokenManager | None = getattr(
        request.app.state, "youtube_token_manager", None
    )
    if tm is None:
        settings = get_settings(request)
        tm = YouTubeTokenManager(
            settings.GOOGLE_DRIVE_CLIENT_ID,
            settings.GOOGLE_DRIVE_CLIENT_SECRET,
            settings.GOOGLE_YOUTUBE_REDIRECT_URI,
        )
        request.app.state.youtube_token_manager = tm
    return tm


def get_youtube_api(request: Request) -> YouTubeAPI:
    settings = get_settings(request)
    return YouTubeAPI(settings.YOUTUBE_API_KEY)


def get_google_oauth_integration(
    settings: Settings = Depends(get_settings),
) -> GoogleOAuthIntegration:
    return GoogleOAuthIntegration(
        settings.GOOGLE_DRIVE_CLIENT_ID,
        settings.GOOGLE_DRIVE_CLIENT_SECRET,
        settings.GOOGLE_LOGIN_REDIRECT_URI,
    )


def get_supabase_auth_integration(
    settings: Settings = Depends(get_settings),
) -> SupabaseAuthIntegration:
    return SupabaseAuthIntegration(
        supabase_url=settings.SUPABASE_URL or "",
        jwt_secret=settings.SUPABASE_JWT_SECRET or "",
        jwks_url=settings.SUPABASE_JWKS_URL or "",
    )


# ── Repositories ───────────────────────────────────────────────────────────


def get_question_repo(
    db: Any = Depends(get_db),
) -> QuestionRepository:
    return QuestionRepository(db)


def get_question_attempt_repo(
    db: Any = Depends(get_db),
) -> QuestionAttemptRepository:
    return QuestionAttemptRepository(db)


def get_question_note_repo(
    db: Any = Depends(get_db),
) -> QuestionNoteRepository:
    return QuestionNoteRepository(db)


def get_mistake_repo(
    db: Any = Depends(get_db),
) -> MistakeRepository:
    return MistakeRepository(db)


def get_pyq_repo(
    db: Any = Depends(get_db),
) -> PYQRepository:
    return PYQRepository(db)


def get_pyq_attempt_repo(
    db: Any = Depends(get_db),
) -> PYQAttemptRepository:
    return PYQAttemptRepository(db)


def get_resource_repo(
    db: Any = Depends(get_db),
) -> ResourceRepository:
    return ResourceRepository(db)


def get_resource_note_repo(
    db: Any = Depends(get_db),
) -> ResourceNoteRepository:
    return ResourceNoteRepository(db)


def get_drive_credential_repo(
    db: Any = Depends(get_db),
) -> DriveCredentialRepository:
    return DriveCredentialRepository(db)


def get_subject_repo(
    db: Any = Depends(get_db),
) -> SubjectRepository:
    return SubjectRepository(db)


def get_analytics_repo(
    db: Any = Depends(get_db),
) -> AnalyticsRepository:
    return AnalyticsRepository(db)


def get_playlist_repo(
    db: Any = Depends(get_db),
) -> PlaylistRepository:
    return PlaylistRepository(db)


def get_video_repo(
    db: Any = Depends(get_db),
) -> VideoRepository:
    return VideoRepository(db)


def get_video_progress_repo(
    db: Any = Depends(get_db),
) -> VideoProgressRepository:
    return VideoProgressRepository(db)


def get_video_note_repo(
    db: Any = Depends(get_db),
) -> VideoNoteRepository:
    return VideoNoteRepository(db)


def get_staging_repo(
    db: Any = Depends(get_db),
) -> StagingQuestionRepository:
    return StagingQuestionRepository(db)


def get_imported_repo(
    db: Any = Depends(get_db),
) -> ImportedQuestionRepository:
    return ImportedQuestionRepository(db)


def get_import_job_repo(
    db: Any = Depends(get_db),
) -> ImportJobRepository:
    return ImportJobRepository(db)


def get_user_repo(
    db: Any = Depends(get_db),
) -> UserRepository:
    return UserRepository(db)


def get_session_repo(
    db: Any = Depends(get_db),
) -> SessionRepository:
    return SessionRepository(db)


def get_oauth_state_repo(
    db: Any = Depends(get_db),
) -> OAuthStateRepository:
    return OAuthStateRepository(db)


def get_youtube_credential_repo(
    db: Any = Depends(get_db),
) -> YouTubeCredentialRepository:
    return YouTubeCredentialRepository(db)


def get_migration_repo(
    db: Any = Depends(get_db),
) -> MigrationRepository:
    return MigrationRepository(db)


def get_search_repo(
    db: Any = Depends(get_db),
) -> SearchRepository:
    return SearchRepository(db)


# ── Services ───────────────────────────────────────────────────────────────


def get_question_service(
    q_repo: QuestionRepository = Depends(get_question_repo),
    att_repo: QuestionAttemptRepository = Depends(get_question_attempt_repo),
    note_repo: QuestionNoteRepository = Depends(get_question_note_repo),
    mistake_repo: MistakeRepository = Depends(get_mistake_repo),
) -> QuestionService:
    return QuestionService(q_repo, att_repo, note_repo, mistake_repo)


def get_question_attempt_service(
    q_repo: QuestionRepository = Depends(get_question_repo),
    att_repo: QuestionAttemptRepository = Depends(get_question_attempt_repo),
) -> QuestionAttemptService:
    return QuestionAttemptService(q_repo, att_repo)


def get_question_note_service(
    note_repo: QuestionNoteRepository = Depends(get_question_note_repo),
) -> QuestionNoteService:
    return QuestionNoteService(note_repo)


def get_question_flag_service(
    q_repo: QuestionRepository = Depends(get_question_repo),
) -> QuestionFlagService:
    return QuestionFlagService(q_repo)


def get_pyq_service(
    pyq_repo: PYQRepository = Depends(get_pyq_repo),
    att_repo: PYQAttemptRepository = Depends(get_pyq_attempt_repo),
) -> PYQService:
    return PYQService(pyq_repo, att_repo)


def get_pyq_attempt_service(
    pyq_repo: PYQRepository = Depends(get_pyq_repo),
    att_repo: PYQAttemptRepository = Depends(get_pyq_attempt_repo),
) -> PYQAttemptService:
    return PYQAttemptService(pyq_repo, att_repo)


def get_oauth_state_service(
    repo: OAuthStateRepository = Depends(get_oauth_state_repo),
) -> OAuthStateService:
    return OAuthStateService(repo)


def get_mistake_service(
    mistake_repo: MistakeRepository = Depends(get_mistake_repo),
) -> MistakeService:
    return MistakeService(mistake_repo)


def get_resource_service(
    res_repo: ResourceRepository = Depends(get_resource_repo),
    note_repo: ResourceNoteRepository = Depends(get_resource_note_repo),
    drive_repo: DriveCredentialRepository = Depends(get_drive_credential_repo),
    subject_repo: SubjectRepository = Depends(get_subject_repo),
    drive: GoogleDriveIntegration = Depends(get_drive_integration),
    oauth_state_service: OAuthStateService = Depends(get_oauth_state_service),
) -> ResourceService:
    return ResourceService(
        res_repo,
        note_repo,
        drive_repo,
        subject_repo,
        drive,
        oauth_state_service,
    )


def get_staging_service(
    staging_repo: StagingQuestionRepository = Depends(get_staging_repo),
    imported_repo: ImportedQuestionRepository = Depends(get_imported_repo),
    import_job_repo: ImportJobRepository = Depends(get_import_job_repo),
) -> StagingService:
    return StagingService(staging_repo, imported_repo, import_job_repo)


def get_youtube_service(
    repo: YouTubeCredentialRepository = Depends(get_youtube_credential_repo),
    token_manager: YouTubeTokenManager = Depends(get_youtube_token_manager),
) -> YouTubeService:
    return YouTubeService(repo, token_manager)


def get_subject_service(
    repo: SubjectRepository = Depends(get_subject_repo),
) -> SubjectService:
    return SubjectService(repo)


def get_analytics_service(
    repo: AnalyticsRepository = Depends(get_analytics_repo),
) -> AnalyticsService:
    return AnalyticsService(repo)


def get_playlist_commands(
    pl_repo: PlaylistRepository = Depends(get_playlist_repo),
    vid_repo: VideoRepository = Depends(get_video_repo),
    prog_repo: VideoProgressRepository = Depends(get_video_progress_repo),
    note_repo: VideoNoteRepository = Depends(get_video_note_repo),
    yt_repo: YouTubeCredentialRepository = Depends(get_youtube_credential_repo),
    token_manager: YouTubeTokenManager = Depends(get_youtube_token_manager),
    yt_api: YouTubeAPI = Depends(get_youtube_api),
) -> PlaylistCommands:
    return PlaylistCommands(
        pl_repo,
        vid_repo,
        prog_repo,
        note_repo,
        yt_repo,
        token_manager,
        yt_api,
    )


def get_playlist_queries(
    pl_repo: PlaylistRepository = Depends(get_playlist_repo),
    vid_repo: VideoRepository = Depends(get_video_repo),
    prog_repo: VideoProgressRepository = Depends(get_video_progress_repo),
) -> PlaylistQueries:
    return PlaylistQueries(pl_repo, vid_repo, prog_repo)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
    session_repo: SessionRepository = Depends(get_session_repo),
) -> UserService:
    return UserService(user_repo, session_repo)


def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repo),
    oauth_state_service: OAuthStateService = Depends(get_oauth_state_service),
    user_service: UserService = Depends(get_user_service),
) -> SessionService:
    return SessionService(session_repo, oauth_state_service, user_service)


def get_supabase_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    supabase_integration: SupabaseAuthIntegration = Depends(
        get_supabase_auth_integration
    ),
) -> SupabaseAuthService:
    return SupabaseAuthService(user_repo, supabase_integration)


def get_identity_repair_service(
    db: Any = Depends(get_db),
) -> IdentityRepairService:
    return IdentityRepairService(db)


def get_search_service(
    repo: SearchRepository = Depends(get_search_repo),
) -> SearchService:
    return SearchService(repo)
