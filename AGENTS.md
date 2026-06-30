# GATEPREP — Project Context

## Stack
- Backend: FastAPI + MongoDB (Motor) + Uvicorn
- Frontend: React + Vite + shadcn/ui + react-pdf
- Auth: Google OAuth (login + Drive + YouTube)

## Rules for the AI
- Do NOT run unnecessary commands (no hidden Start-Process, no zombie processes).
- Do NOT add unnecessary code — every addition must be justified.
- Do NOT modify unrelated files — only touch files relevant to the task.
- Always write production-grade, industry-standard code.
- Always choose the best system design — no shortcuts.
- Always ask before committing/pushing to GitHub.

## Drive OAuth Issue (unresolved)
- Google Drive redirect URI `http://localhost:8001/api/drive/callback` is registered in Google Cloud Console and set in `backend/.env`, but Drive connect still fails with `redirect_uri_mismatch`.
- YouTube OAuth works fine with the same pattern.
- Needs investigation later.

## Completed Phases
- Phase 0: Git sync, cleanup, backup branch
- Phase 1: Vite migration, rebrand (GATE Study OS → GATEPREP), remove admin/difficulty, dead code deletion, backend restructure (split core.py, extract schemas/constants/utils)
- Phase 2: Security hardening (slowapi rate limiting, auth on all endpoints, security headers, custom exception handler, input validation via Pydantic max_length, dev-login gated by ENVIRONMENT, 200MB upload limit)
- Phase 3: YouTube OAuth (per-user tokens replace shared API key, OAuth endpoints, Settings UI)

## Current State
- Backend runs on port 8001 (port 8000 stuck in TIME_WAIT earlier, now clear)
- Frontend runs on port 3000 (Vite dev server)
- Drive OAuth: connected before but now broken after port change (redirect_uri_mismatch — needs fixing)
- YouTube OAuth: connected and import verified working
- PDF viewer: PdfCanvasViewer with notes panel + bookmarks (annotation layer disabled)

## Key Constraints
- No `is_admin` field or admin role anywhere
- No `difficulty` field anywhere
- Resource Drive sync only on first login or after upload (not on every page visit)
- Subjects/topics endpoints require auth (no public access)
- Password/email auth not yet implemented (Phase 4)

## Key Files
- `backend/routes/resources.py` — Drive OAuth, PDF streaming (download-to-memory)
- `backend/routes/playlists.py` — Playlist CRUD, video tracking, YouTube import
- `backend/routes/youtube.py` — YouTube OAuth endpoints (auth, callback, status, disconnect)
- `backend/routes/subjects.py` — Subject/topic listing (auth-protected)
- `backend/routes/auth.py` — Login, session, dev-login
- `backend/server.py` — CORS, rate limiter, security headers, exception handler
- `backend/schemas.py` — Pydantic models with validation
- `backend/limiter.py` — Shared slowapi instance
- `frontend/src/pages/Resources.jsx` — Resource listing + PDF viewer state
- `frontend/src/components/PdfCanvasViewer.jsx` — PDF viewer (blob-based)
- `frontend/src/pages/Settings.jsx` — Drive + YouTube connect UI

## What's Next
- Fix Drive OAuth redirect_uri_mismatch (investigate)
- Phase 4: Email/password auth (Supabase or Auth0 — TBD)
- Phase 5: Full restructure (app/ package architecture)

## How to Start
```powershell
# Backend (Window 1)
cd backend
& ../venv/Scripts/python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001

# Frontend (Window 2)
cd frontend
node_modules/.bin/vite.cmd --host 127.0.0.1 --port 3000
```
