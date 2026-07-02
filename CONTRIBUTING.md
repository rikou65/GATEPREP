# Contributing to GATEPREP

This document is for developers contributing to the project. For project
architecture and active execution order, read `ARCHITECTURE.md` and
`IMPLEMENTATION_ROADMAP.md` first.

## Read First

1. [README.md](./README.md)
2. [ARCHITECTURE.md](./ARCHITECTURE.md)
3. [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
4. [OCR_PIPELINE.md](./OCR_PIPELINE.md) if touching OCR/staging

## Local Setup

Backend:

```powershell
cd backend
& ../venv/Scripts/python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
cd frontend
node_modules/.bin/vite.cmd --host 127.0.0.1 --port 3000
```

## Core Rules

- All user-owned reads and writes must be scoped by `user_id`
- No `is_admin` role model anywhere
- No `difficulty` field anywhere
- Use `VITE_*` frontend env variables
- Do not reintroduce legacy `/api/admin/*` staging routes
- Keep Question Bank and PYQs separate
- Keep route handlers thin when feasible

## Frontend Conventions

- Use the shared API client from `frontend/src/lib/api.js`
- Prefer existing UI primitives before adding dependencies
- Keep server state separate from UI-only state
- Preserve in-context study flows and avoid noisy UX

## Backend Conventions

- Validate request payloads with canonical schemas
- Avoid duplicated route-local schemas when shared models exist
- Verify ownership through parent entities where needed
- Prefer service/repository extraction when route logic becomes stateful

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

When changing playlists, include regression coverage for:

- resume to the correct video and timestamp
- watched videos staying watched when other videos start
- queue visibility and centering behavior
- notes autosave not firing on unchanged blur
- ownership checks on video progress and notes

## Documentation Rules

- Update `README.md` if setup or public project description changes
- Update `ARCHITECTURE.md` if domain shape or major pain points change
- Update `IMPLEMENTATION_ROADMAP.md` when priorities or phase content change
- Update `OCR_PIPELINE.md` if OCR routes or staging flow change
