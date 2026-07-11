from __future__ import annotations

"""GATEPREP — FastAPI application factory."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.subjects import router as subjects_router
from app.api.endpoints.practice import router as practice_router
from app.api.endpoints.analytics import router as analytics_router
from app.api.endpoints.playlists import router as playlists_router
from app.api.endpoints.resources import router as resources_router
from app.api.endpoints.youtube import router as youtube_router
from app.api.endpoints.staging import router as staging_router
from app.api.responses import ok
from app.core.config import Settings
from app.core.db import create_db_client
from app.core.logging import logger
from app.core.time import iso, now_utc
from app.repositories.oauth_states import OAuthStateRepository

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

settings = Settings(_env_file=str(ROOT_DIR / ".env"))

client, db = create_db_client(settings)


def create_app() -> FastAPI:
    app = FastAPI(title="GATEPREP")
    app.state.settings = settings
    app.state.db = db
    app.state.client = client

    _setup_middleware(app)
    _mount_routes(app)
    _setup_error_handlers(app)
    _setup_lifespan(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
    allowed_origins: list[str] = []
    if settings.is_production():
        if frontend_url:
            allowed_origins.append(frontend_url)
    else:
        allowed_origins = ["http://127.0.0.1:3000", "http://localhost:3000"]
        if frontend_url and frontend_url not in allowed_origins:
            allowed_origins.append(frontend_url)

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


def _mount_routes(app: FastAPI) -> None:
    from fastapi import APIRouter

    api = APIRouter(prefix="/api")

    api.include_router(auth_router)
    api.include_router(subjects_router)
    api.include_router(practice_router)
    api.include_router(analytics_router)
    api.include_router(playlists_router)
    api.include_router(resources_router)
    api.include_router(youtube_router)
    api.include_router(staging_router, prefix="/data")

    @api.get("/")
    async def root():
        return {"service": "gateprep", "version": "1.0"}

    @api.get("/health")
    async def health():
        return {"status": "ok", "ts": iso(now_utc())}

    app.include_router(api)


def _setup_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=()"
            )
        return response


def _setup_lifespan(app: FastAPI) -> None:
    @app.on_event("startup")
    async def on_startup():
        from app.bootstrap.seed import seed_data
        from app.bootstrap import migrations
        from app.bootstrap.migrations import (
            _migrate_v2_split_subjects,
            _migrate_per_user_content,
            _ensure_runtime_indexes,
            _purge_global_staging_records,
        )
        migrations.configure(db)

        if await db.subjects.count_documents({}) == 0:
            result = await seed_data(db)
            logger.info(f"Seeded GATE syllabus: {result}")

        await _migrate_v2_split_subjects()
        await _migrate_per_user_content()
        await _purge_global_staging_records()

        oauth_state_repo = OAuthStateRepository(db)
        await oauth_state_repo.ensure_index()
        await _ensure_runtime_indexes()
        logger.info("GATEPREP new app started")

    @app.on_event("shutdown")
    async def on_shutdown():
        client.close()


app = create_app()
