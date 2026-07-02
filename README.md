# GATEPREP

GATEPREP is a personal, multi-tenant study platform for GATE CSE preparation.
It combines a private question bank, PYQs, mistakes, YouTube playlist tracking,
Google Drive-backed resources, and OCR ingestion into one workspace.

## Source-of-Truth Docs

If another coding agent needs to start working on this repo, these are the
documents that matter:

- [ARCHITECTURE.md](./ARCHITECTURE.md) — current system shape and domain map
- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) — active roadmap and
  execution order
- [OCR_PIPELINE.md](./OCR_PIPELINE.md) — OCR import and staging design
- [CONTRIBUTING.md](./CONTRIBUTING.md) — coding conventions and guardrails
- [AGENTS.md](./AGENTS.md) — local project instructions for AI coding agents

## Current Product Domains

- `auth`: Google login, session lifecycle, dev login
- `subjects`: official GATE CSE subject and topic taxonomy
- `practice`: question bank, PYQs, attempts, notes, flags, mistakes
- `analytics`: dashboard, subject analytics, topic analytics
- `playlists`: YouTube playlist import, video progress, video notes
- `resources`: Drive-backed library, PDF viewer, resource notes
- `drive`: Drive OAuth, sync, upload, streaming proxy
- `youtube`: YouTube OAuth and token lifecycle
- `ocr`: PDF import, OCR pipeline, staging queue, approval flow

## Tech Stack

- Backend: FastAPI + Motor + MongoDB
- Frontend: React + Vite + Tailwind + shadcn/ui
- Auth: Google OAuth + session cookies
- Storage: MongoDB metadata + user-owned Google Drive files
- OCR: Mistral OCR + structured extraction into staging collections

## Current Local Reality

- Frontend dev server: `http://127.0.0.1:3000`
- Backend API: `http://127.0.0.1:8001/api`
- Frontend env prefix: `VITE_*`
- Canonical frontend backend env: `VITE_BACKEND_URL`
- Staging and OCR routes live under `/api/data/*`
- Legacy `/api/admin/*` routes are retired

## Local Development

### Backend

```powershell
cd backend
& ../venv/Scripts/python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001
```

### Frontend

```powershell
cd frontend
node_modules/.bin/vite.cmd --host 127.0.0.1 --port 3000
```

## Environment Variables

### `frontend/.env`

```env
VITE_BACKEND_URL=http://127.0.0.1:8001
VITE_GOOGLE_CLIENT_ID=
VITE_GOOGLE_LOGIN_REDIRECT_URI=http://127.0.0.1:3000/auth/callback
```

### `backend/.env`

Required core variables:

- `MONGO_URL`
- `DB_NAME`
- `JWT_SECRET`
- `GOOGLE_DRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET`
- `GOOGLE_LOGIN_REDIRECT_URI`
- `GOOGLE_DRIVE_REDIRECT_URI`
- `GOOGLE_YOUTUBE_REDIRECT_URI`
- `FRONTEND_URL`

Optional/feature-specific:

- `YOUTUBE_API_KEY`
- `MISTRAL_API_KEY`
- `ENVIRONMENT`

## Important Product Rules

- Every user-owned collection must be scoped by `user_id`
- No `is_admin` role model anywhere
- No `difficulty` field anywhere
- QBank and PYQs stay separate
- Playlist videos belong to playlists, and playlist operations must verify
  ownership through the parent playlist
- Resource files stay user-owned in Google Drive

## Testing

Frontend:

```powershell
cd frontend
npm run build
```

Backend:

```powershell
cd backend
pytest -v
```

## What Changed Recently

- Vite is now the active frontend toolchain
- Local backend standard is port `8001`
- Roadmap has been replaced with a 10-phase architecture roadmap
- Playlist reliability issues have been added to the roadmap in detail

## Notes For Another Coding Agent

Before making changes:

1. Read [ARCHITECTURE.md](./ARCHITECTURE.md)
2. Read [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
3. If touching OCR, read [OCR_PIPELINE.md](./OCR_PIPELINE.md)
4. Follow [CONTRIBUTING.md](./CONTRIBUTING.md)
5. Treat the roadmap as the source of truth over older assumptions in the code
