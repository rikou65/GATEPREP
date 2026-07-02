# GATEPREP Architecture

GATEPREP is a personal, multi-tenant study platform for GATE CSE preparation.

## Current Domains

- `auth`: Google login, session cookie lifecycle, dev-login for local development
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
- Frontend: React + Vite + shadcn/ui + react-pdf
- Auth: session cookie backed by `user_sessions`
- Storage: user-owned metadata in MongoDB, user-owned files in Google Drive
- OCR: Mistral OCR + structured parse into staging documents

## Current Pain Points

- Several route files still mix transport, business logic, and data access.
- Validation, constants, and helper utilities are duplicated in multiple places.
- Some frontend pages own too much state and orchestration logic.
- Playlist resume, queue state, and player-progress synchronization are currently unreliable.
- Docs and live code have drifted on routes, env names, and local ports.

## Refactor Direction

- Keep `/api` as the canonical backend prefix.
- Keep user-owned collections explicitly scoped by `user_id`.
- Move backend toward layered architecture: API, services, repositories, schemas, and core utilities.
- Move frontend toward feature-based folders, shared API modules, and reusable hooks for server-driven state.
