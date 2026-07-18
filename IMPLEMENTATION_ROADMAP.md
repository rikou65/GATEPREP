# GATEPREP — Implementation Roadmap

> **Current verification:** The refactor and dependency cleanup have passed localhost manual testing. Re-test localhost after future backend/frontend behavior changes.

## Summary

This roadmap replaces the older implementation roadmap as the source of truth.
Completed work still stands, but active work now prioritizes correctness, security,
maintainability, and then scale.

---

## Phase 0 — Baseline, Safety, and Repo Hygiene

**Goal:** make the repo trustworthy before larger refactors begin.

- [x] Ignore generated cache folders like `.vite/`
- [x] Keep large PDF source folders (`GATE_OVERFLOW/`, `UNACADEMY/`) out of git
- [x] Create a backup branch before architecture refactor (`backup-before-refactor-20260705`)
- [x] Remove generated cache folders from local worktree as needed
- [x] Update docs to match live reality:
  - Vite is the active frontend toolchain
  - `VITE_BACKEND_URL` is canonical
  - local backend runs on `8001`
  - staging/import routes are `/api/data/*`
  - `/api/admin/*` is retired
  - Drive OAuth is non-blocking after repeated successful localhost manual tests
- [x] Add `ARCHITECTURE.md` with the current domain map

---

## Phase 1 — P0 Stabilization and Broken Flow Fixes

**Goal:** remove current user-facing bugs and route/config drift before deeper work.

- [x] Fix frontend route drift:
  - replace stale `/admin/*` frontend calls with `/data/*`
  - change OCR import success navigation from `/admin/staging` to `/data/staging`
- [x] Fix Resources Drive false popup:
  - remove stale React-state dependency in `runSync`
  - scope `driveSyncNeeded` by `user_id`
  - do not set Drive sync needed on dev-login unless Drive is actually connected
- [x] Remove remaining `difficulty` UI/state from Question Bank and Question Form
- [x] Fix local config consistency:
  - `frontend/src/lib/api.ts` fallback matches local backend `8001`
  - login UI does not mention port `8000`
- [x] Fix hardcoded Google login config:
  - Supabase Google login is configured through Supabase client env
  - legacy Google login URL is built server-side
  - backend env examples include login and YouTube redirect URI coverage
- [x] Fix playlist correctness and resume flow:
  - progress writes always target the active `video_id`
  - playlists reopen on the most relevant in-progress or recently watched video
  - saved `watch_time` is restored without being overwritten by a fresh playback start
  - manually marked watched videos stay watched until explicitly unmarked
- [x] Fix playlist notes UX:
  - unchanged blur events do not autosave or show save toasts
  - autosave feedback is quiet and stateful
- [x] Fix playlist queue behavior:
  - queue behaves as a controlled 3-card carousel
  - active video stays centered when possible
  - next/manual navigation snaps to valid queue windows

---

## Phase 2 — Security and Multi-Tenant Isolation (completed)

**Goal:** close current security gaps before the large refactor.

- [x] Make staging fully tenant-scoped:
  - store and filter OCR/staging records by `user_id`
  - prevent approving, deleting, or clearing another user's staging data
- [x] Fix IDOR gaps:
  - ownership checks for mistakes, playlist progress, video notes, and analytics joins
- [x] Harden OAuth:
  - random, expiring, single-use state records for login, Drive, and YouTube OAuth
- [x] Harden uploads and URL imports:
  - PDF validation, upload size limits, private-network blocking, and response size limits
- [x] Harden production settings:
  - no invalid TLS in production
  - secure cookies in production
  - CSP/HSTS/Permissions-Policy headers

---

## Phase 3 — Backend Full Refactor (completed)

**Goal:** move the backend to layered architecture with thin routes and central rules.

- [x] Move backend into `app/` package architecture:
  - `app/main.py`
  - `app/api/endpoints/`
  - `app/services/`
  - `app/repositories/`
  - `app/schemas/`
  - `app/core/`
- [x] Split domains into explicit backend modules:
  - `auth`, `subjects`, `questions`, `pyqs`, `mistakes`, `analytics`, `playlists`, `resources`, `drive`, `youtube`, `ocr_import`, `staging`
- [x] Make route handlers transport-only:
  - validate input
  - call services
  - return responses
- [x] Add `app/api/providers.py` as the single Depends-wired provider layer for repositories, services, and integrations
- [x] Move business rules into services:
  - latest-attempt accuracy
  - ownership checks
  - playlist resume-target selection
  - explicit watched/unwatched semantics instead of deriving all completion state from percentage alone
  - playlist delete cascade rules for videos, progress, and notes
  - Drive token refresh and sync
  - OCR job/staging lifecycle
  - question/PYQ approval flow
- [x] Move all Mongo access into repositories with mandatory `user_id` filtering for user-owned collections
- [x] Move Mongo aggregation pipeline builders for Question Bank/PYQs out of services into repository query helpers
- [x] Add playlist repository helpers for:
  - ownership-checked playlist/video lookups
  - latest watched or in-progress video resolution
  - playlist cleanup and video-note cascade deletion
- [x] Remove duplicated helpers and models:
  - use one canonical `schemas`, `constants`, `time`, `id`, and response layer
  - replace route-local schemas with canonical validated models
  - delete or migrate stale backend helpers and unused constants

---

## Phase 4 — Frontend Full Refactor

**Goal:** move from page-heavy orchestration to feature-oriented frontend architecture.

- [x] Restructure frontend partially:
  - `src/api/` (typed client, query keys, endpoint modules)
  - `src/features/auth/` (hooks/useAuth.js)
  - `src/features/subjects/` (hooks/useSubjects.js)
- [x] Restructure remaining frontend data access into feature hooks:
  - `questions`, `pyqs`, `resources`, `playlists`, `ocr`, `analytics`, `mistakes`
- [x] Replace repeated page-level data fetching with reusable hooks:
  - auth/session, settings integrations, dashboard/analytics
  - subjects/topics, questions, PYQs, mistakes
  - resources/Drive, playlists/video notes/progress, staging/import jobs
- [ ] Extract large UI orchestration only where it reduces complexity:
  - resource viewer state
  - playlist player lifecycle
  - [x] playlist queue visibility behavior moved into feature hooks
  - [x] playlist notes dirty-state and autosave behavior moved into feature hooks
- [x] Centralize route paths and API paths so components never hardcode `/admin/*`, ports, or OAuth URLs
- [x] Adopt React Query infrastructure: QueryClientProvider, typed API client, query keys, endpoint modules
- [ ] Separate playlist concerns inside the frontend:
  - player lifecycle and progress sync
  - resume behavior
  - [x] queue visibility logic
  - [x] notes dirty-state and autosave behavior
- [x] Add app-level error handling:
  - 404 page
  - 500/error boundary
  - auth-expired handling
  - consistent toast/error presentation

---

## Phase 5 — Testing, Quality Gates, and Developer Workflow

**Goal:** make refactors safe and repeatable.

- [x] Replace server-spawning tests with FastAPI client-based testing
- [x] Split tests into:
  - unit tests for pure logic and services
  - API tests for route contracts
  - integration tests for Mongo-backed flows
- [ ] Add required regression coverage for:
  - multi-user isolation
  - staging approve/delete/clear isolation
  - Resources Drive connected-state race
  - OAuth state verification
  - upload validation and URL import blocking
  - latest-attempt accuracy behavior
  - playlist resume target selection
  - watched videos remaining watched when another video starts playing
  - [x] progress writes always targeting the correct active video
  - notes blur with unchanged content not triggering save toast
  - queue auto-centering and 3-card window behavior
  - [x] Question Bank/PYQ pagination API contracts
- [ ] Add frontend coverage for critical flows:
  - login callback
  - Resources Drive connected state
  - staging queue actions
  - question/PYQ filtering and submission
  - reopening a playlist resumes the correct video and timestamp
  - `Next Video` shifts the queue and keeps the active card visible/centered when possible
  - marking one video watched does not clear another video’s watched state
- [x] Add project tooling:
  - backend Ruff/Black config
  - frontend ESLint config with TypeScript parsing
  - CI for backend tests, frontend build, and lint checks
- [x] Split backend dependency files:
  - runtime dependencies in `backend/requirements.txt`
  - dev/test tools in `backend/requirements-dev.txt`
  - verified with a temporary clean venv
- [x] Add architecture guardrails:
  - frontend raw API calls stay in endpoint modules
  - frontend endpoint modules are consumed through feature hooks
  - backend runtime layers do not use direct Mongo collection access
  - backend endpoints do not import repositories/integrations or access `request.app.state.db`
  - docs do not mention deleted backend entrypoints

---

## Phase 6 — OCR Production Readiness

**Goal:** make OCR durable, isolated, and operationally safe.

- [ ] Replace FastAPI `BackgroundTasks` with a durable queue (`Redis` + `ARQ`/`RQ`)
- [x] Make OCR jobs tenant-scoped end to end
- [ ] Implement OCR image extraction:
  - store raw OCR images with `user_id`, `job_id`, page, mime type, and image ID
  - serve through `/api/data/ocr-images/{image_id}` with ownership checks
  - render extracted images in staging and question content
- [ ] Add OCR quotas:
  - per-user page cap
  - max file size
  - max concurrent jobs per user
- [ ] Add retry and cleanup semantics:
  - chunk retry
  - failed job dismissal
  - safe temp-file and provider-file cleanup

---

## Phase 7 — UX, Performance, and Data Scale

**Goal:** improve responsiveness once correctness and architecture are stable.

- [x] Add DB indexes:
  - attempts by `(user_id, question_id)` and `(user_id, pyq_id)`
  - staging by `(user_id, status)`
  - content by `(user_id, subject_id, topic_id)`
  - resources/playlists by `(user_id, subject_id)`
  - `video_progress` by `(user_id, video_id)` and `(user_id, last_watched_at)`
  - `video_notes` by `(user_id, video_id)`
- [ ] Add pagination:
  - [x] Question Bank and PYQs at 50 per page
  - staging queue pagination or virtualization
- [ ] Make resource streaming truly streaming and avoid loading full Drive files into memory
- [x] Add skeleton/loading states across major pages
- [ ] Optimize playlist queue behavior for long playlists with a fixed 3-card viewport and controlled navigation instead of raw scroll dependence
- [x] Add global search:
  - [x] backend `/api/search`
  - [x] frontend Cmd/Ctrl+K overlay
  - questions, PYQs, resources, subjects, and topics
- [ ] Add optional Redis caching for dashboard and analytics after indexing is complete

---

## Phase 8 — Auth, Account, Deployment, and Compliance

**Goal:** make the product production-ready around accounts and deployment.

- [x] Decide auth provider before email/password implementation:
  - selected: Supabase Auth, with MongoDB remaining the application database
- [x] Add email/password flows after provider selection:
  - signup
  - login
  - forgot/reset password
  - email verification is controlled in Supabase project settings
  - change password remains future account-settings work
- [x] Keep Google login as a first-class auth option
- [ ] Expand account settings:
  - Drive connection
  - YouTube connection
  - session/logout
  - future account deletion
- [ ] Harden deployment:
  - production env documentation
  - production CORS allowlist
  - health checks for DB and external APIs
- [ ] Add legal/compliance pages:
  - privacy policy
  - terms
  - contact/support
  - cookie or analytics consent if applicable

---

## Phase 9 — Advanced Product Features

**Goal:** build advanced study features on top of a stable core.

- [ ] OCR/math improvements:
  - full KaTeX integration
  - stronger table/K-map rendering
  - image-aware question rendering
- [ ] Study features:
  - SM-2 spaced repetition in Mistake Lab
  - Mock Test mode
  - daily goals and streaks
  - offline/PWA support
- [ ] AI features:
  - chat with notes/resources
  - retrieval over user-owned PDFs and notes
  - study recommendations from latest-attempt signal
- [ ] Export/import:
  - question bank export
  - optional Anki export
  - backup/restore user data

---

## Standards

- `/api` remains the canonical backend prefix
- staging and OCR routes remain under `/api/data/*`
- frontend env standard is `VITE_*`
- user-owned collections must include `user_id`
- route/service/repository layers must keep user context explicit
