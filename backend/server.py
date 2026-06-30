"""GATEPREP - FastAPI backend (MongoDB)."""
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from shared import client, db, logger, ok
from seed import seed_data
from migrations import _migrate_v2_split_subjects, _migrate_per_user_content, _ensure_flag_indexes
from limiter import limiter
from slowapi import _rate_limit_exceeded_handler

from routes.auth import router as auth_router
from routes.subjects import router as subjects_router
from routes.analytics import router as analytics_router
from routes.practice import router as practice_router
from routes.playlists import router as playlists_router
from routes.resources import router as resources_router
from routes.admin_staging import router as admin_staging_router
from routes.youtube import router as youtube_router
from shared import settings

app = FastAPI(title="GATEPREP")
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

api = APIRouter(prefix="/api")

# mount extracted routes
api.include_router(auth_router)
api.include_router(subjects_router)
api.include_router(analytics_router)
api.include_router(practice_router)
api.include_router(playlists_router)
api.include_router(resources_router)
api.include_router(admin_staging_router, prefix="/data")
api.include_router(youtube_router)

# basic health endpoints
@api.get("/")
async def root():
    return {"service": "gateprep", "version": "1.0"}

@api.get("/health")
async def health():
    from shared import now_utc, iso
    return {"status": "ok", "ts": iso(now_utc())}

app.include_router(api)

# CORS middleware
frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
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

# Custom exception handler — return JSON instead of raw traceback
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.on_event("startup")
async def on_startup():
    """Startup hook: auto-seed, run migrations, create indexes."""
    try:
        if await db.subjects.count_documents({}) == 0:
            result = await seed_data()
            logger.info(f"Seeded GATE syllabus: {result}")
        await _migrate_v2_split_subjects()
        await _migrate_per_user_content()
        await _ensure_flag_indexes()
    except Exception as e:
        logger.error(f"Startup error: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()

