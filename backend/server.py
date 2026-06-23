"""GATE Study OS - FastAPI backend (MongoDB)."""
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from shared import client, db, logger, ok
from seed import seed_data
from migrations import _migrate_v2_split_subjects, _migrate_per_user_content, _ensure_flag_indexes

from routes.core import router as core_router
from routes.analytics import router as analytics_router
from routes.practice import router as practice_router
from routes.playlists import router as playlists_router
from routes.resources import router as resources_router
from routes.admin_staging import router as admin_staging_router

app = FastAPI(title="GATE Study OS")
api = APIRouter(prefix="/api")

# mount extracted routes
api.include_router(core_router)
api.include_router(analytics_router)
api.include_router(practice_router)
api.include_router(playlists_router)
api.include_router(resources_router)
api.include_router(admin_staging_router, prefix="/admin")

# basic health endpoints
@api.get("/")
async def root():
    return {"service": "gate-study-os", "version": "1.0"}

@api.get("/health")
async def health():
    from shared import now_utc, iso
    return {"status": "ok", "ts": iso(now_utc())}

app.include_router(api)

# CORS middleware
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

