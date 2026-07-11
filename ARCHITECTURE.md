# GATEPREP Architecture

GATEPREP is a personal, multi-tenant study platform for GATE CSE preparation.

## Current Domains

- `auth`: Supabase login, temporary legacy Google fallback, session cookie lifecycle, dev-login for local development
- `subjects`: official syllabus subjects and topics
- `practice`: Question Bank, PYQs, attempts, notes, flags, and mistakes
- `analytics`: dashboard, subject analytics, and topic analytics
- `playlists`: YouTube playlist import, video progress, and video notes
- `resources`: resource CRUD, resource notes, PDF viewing, and Drive-backed file access
- `drive`: Drive OAuth, token refresh, Drive sync, Drive uploads, and streaming proxy
- `youtube`: YouTube OAuth and token lifecycle
- `ocr`: PDF import, OCR job execution, staging queue, and approval flow

## Current Technical Shape

- Backend: FastAPI + Motor + MongoDB
- Frontend: React + Vite + shadcn/ui + react-pdf + TanStack React Query
- Auth: session cookie backed by `user_sessions`; OAuth state hardened (random, expiring, single-use); Supabase primary auth with temporary legacy cookie/Google fallback
- Storage: user-owned metadata in MongoDB, user-owned files in Google Drive
- OCR: Mistral OCR + structured parse into staging documents (tenant-isolated in Phase 2)
- Architecture: Layered — endpoints → services → repositories → MongoDB; integrations for external providers

## Current Pain Points

- Backend runtime layers now obey endpoints → services → repositories → MongoDB.
- Frontend server access is centralized in `frontend/src/api/endpoints/*`; pages consume wrappers/hooks.
- Some large frontend screens still own substantial UI orchestration state.
- Playlist resume, queue state, and player-progress synchronization are currently unreliable. (resolved in Phase 1 playlist fixes)
- Docs and live code have drifted on routes, env names, and local ports. (partially resolved in Phase 2 — login URL now server-generated)

## Current Architecture

The backend now uses a layered architecture under `backend/app/`:

```
app/
  main.py            — FastAPI factory (new entry point)
  api/
    deps.py          — get_current_user (dual-auth: legacy cookie or Supabase JWT)
    responses.py     — ok(), err() helpers
    endpoints/       — auth, subjects, practice, analytics, playlists, resources, youtube, staging
  core/              — config, db, time, ids, security, constants, logging
  schemas/           — canonical Pydantic models per domain
  services/          — business logic (orchestration)
  repositories/      — MongoDB access only
  integrations/      — external API clients (google_oauth, supabase_auth, google_drive, google_youtube)
  bootstrap/         — startup seed/migration code; allowed to use Mongo directly
  tasks/             — background workers (placeholder)
```

## Refactor Direction

- Keep `/api` as the canonical backend prefix.
- Keep user-owned collections explicitly scoped by `user_id`.
- Keep raw Axios calls inside `frontend/src/api/endpoints/*`.
- Migrate remaining large UI orchestration to feature hooks only when it reduces complexity.

## Legacy Google Removal Checklist

Legacy Google login remains as a temporary fallback. Remove `/auth/google-url`
and `/auth/session` only after:

- Supabase Google redirect is verified on localhost and production.
- Supabase email login/signup is verified.
- Same verified email maps to the same internal `user_id`.
- Drive and YouTube OAuth continue to use their separate Google flows.
- Existing local user data is visible after Supabase login.
