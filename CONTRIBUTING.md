# Contributing to GATEPREP

This repo is optimized for correctness, tenant isolation, and maintainability.
If you are a human contributor or another coding agent, use this file together
with `ARCHITECTURE.md` and `IMPLEMENTATION_ROADMAP.md`.

## Read These First

1. [ARCHITECTURE.md](./ARCHITECTURE.md)
2. [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
3. [OCR_PIPELINE.md](./OCR_PIPELINE.md) if you are touching OCR/staging
4. [AGENTS.md](./AGENTS.md) if you are an AI coding agent working locally

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

## Core Engineering Rules

- All user-owned reads and writes must be scoped by `user_id`
- No `is_admin` role model anywhere
- No `difficulty` field anywhere
- No stale `/api/admin/*` additions; staging/OCR live under `/api/data/*`
- Use `VITE_*` frontend env variables, not `REACT_APP_*`
- Keep QBank and PYQs separate
- Keep question/PYQ solutions inline
- Keep route handlers thin when touching backend code

## Frontend Rules

- Use the shared API client from `frontend/src/lib/api.js`
- Prefer existing shadcn primitives before adding new UI libraries
- Keep server state separate from UI-only state
- Playlist UI must preserve active video, watched state, and queue state
- Do not render raw LaTeX strings directly when existing math rendering helpers
  are already in use for the relevant surface

## Backend Rules

- Validate request payloads with canonical schemas
- Avoid route-local duplicate schemas when shared ones exist
- Verify ownership through parent entities where needed:
  - playlist video operations must verify video ownership through the parent playlist
  - resource operations must verify resource ownership
- Prefer repository/service extraction when route logic becomes stateful or
  cross-cutting

## Testing Expectations

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
- queue centering/visibility behavior
- notes autosave not firing on unchanged blur
- ownership checks on video progress and notes

## Documentation Rules

- Update `README.md` if local setup or source-of-truth docs change
- Update `ARCHITECTURE.md` if domain boundaries or major pain points change
- Update `IMPLEMENTATION_ROADMAP.md` when priorities or phase content change
- Update `OCR_PIPELINE.md` if OCR routes, staging flow, or extraction behavior changes
