# GATEPREP — Implementation Roadmap

> **Note:** Localhost testing by the user is not yet done. All refactors need manual verification on localhost before they can be considered fully complete.

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
- [ ] Remove generated cache folders from local worktree as needed
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
- [x] Fix Resources Drive false popup: (completed)
  - remove stale React-state dependency in `runSync` (completed)
  - scope `driveSyncNeeded` by `user_id` (completed)
  - do not set Drive sync needed on dev-login unless Drive is actually connected (completed)
- [x] Remove remaining `difficulty` UI/state from Question Bank and Question Form
- [x] Fix local config consistency:
  - `frontend/src/lib/api.ts` fallback matches local backend `8001`
  - login UI does not mention port `8000`
- [x] Fix hardcoded Google login config:
  - Supabase Google login is configured through Supabase client env
  - legacy Google login URL is built server-side
  - backend env examples include login and YouTube redirect URI coverage
- [x] Fix playlist correctness and resume flow: (completed)
  - stop stale player callbacks from writing progress to the wrong video after switching active videos (completed)
  - ensure playback/progress sync always targets the currently active `video_id` (completed)
  - reopen a playlist on the most recently in-progress or most recently watched video instead of always index `0` (completed)
  - restore saved `watch_time` when reopening a video (completed)
  - stop saved progress from being immediately overwritten by a fresh `0%` playback start (completed)
  - keep manually marked watched videos watched until the user explicitly unmarks them (completed)
- [x] Fix playlist notes UX: (completed)
  - do not save notes on blur when content is unchanged (completed)
  - do not show `Notes saved` for no-op autosaves (completed)
  - keep autosave feedback quiet and stateful instead of toast-heavy (completed)
- [x] Fix playlist queue behavior: (completed)
  - treat the queue as a controlled 3-card carousel, not a raw horizontal scroller (completed)
  - keep the active video card centered when possible (completed)
  - auto-shift the queue when `Next Video` activates a card outside the visible 3-card window (completed)
  - make manual scrolling snap back to valid 3-card windows (completed)
  - replace browser-like double-click queue shifting with deterministic one-step movement (completed)

---

## Phase 2 — Security and Multi-Tenant Isolation (completed)

**Goal:** close current security gaps before the large refactor.

- [x] Make staging fully tenant-scoped: (completed)
  - store `user_id` on `import_jobs`, `staging_questions`, `topic_concepts`, and future `ocr_images` (completed)
  - filter list, delete, clear, approve-specific, and bulk-approve by `user_id` (completed)
  - prevent approving or deleting another user’s staging item (completed)
- [x] Fix IDOR gaps: (completed)
  - `create_mistake` must fetch question with `user_id` (completed)
  - video progress must verify `video_id` ownership through the parent playlist before writes (completed)
  - video notes must verify `video_id` ownership through the parent playlist before reads and writes (completed)
  - analytics joins must avoid counting or exposing another user’s content (completed)
- [x] Harden OAuth: (completed)
  - replace raw `user_id` OAuth state with random, expiring, session-bound state records (completed)
  - apply to Drive and YouTube OAuth (completed)
- [x] Harden uploads and URL imports: (completed)
  - validate extension, MIME type, and PDF magic bytes (completed)
  - add OCR upload size limit (completed)
  - block localhost/private-network/non-HTTP(S) URL imports and oversized responses (completed)
- [x] Harden production settings: (completed)
  - remove `tlsAllowInvalidCertificates=True` outside local development (completed)
  - use secure cookies in production (completed)
  - add CSP, HSTS, and audit logging for sensitive actions (completed: HSTS, CSP/PP; audit logging pending)

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
- [x] Move business rules into services:
  - latest-attempt accuracy
  - ownership checks
  - playlist resume-target selection based on `completed`, `watch_percentage`, `watch_time`, and `last_watched_at`
  - explicit watched/unwatched semantics instead of deriving all completion state from percentage alone
  - playlist delete cascade rules for videos, progress, and notes
  - Drive token refresh and sync
  - OCR job/staging lifecycle
  - question/PYQ approval flow
- [x] Move all Mongo access into repositories with mandatory `user_id` filtering for user-owned collections
- [x] Add playlist repository helpers for:
  - ownership-checked playlist/video lookups
  - latest watched or in-progress video resolution
  - playlist cleanup and video-note cascade deletion
- [x] Remove duplicated helpers and models:
  - use one canonical `schemas`, `constants`, `time`, `id`, and response layer
  - replace route-local playlist progress schemas with canonical validated models (done in app/)
  - delete or migrate stale `backend/utils/*`, route-local schemas, and unused constants

---

## Phase 4 — Frontend Full Refactor

**Goal:** move from page-heavy orchestration to feature-oriented frontend architecture.

- [x] Restructure frontend partially:
  - `src/api/` (client.js, queryKeys.js, endpoints/)
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
  - playlist queue window and centering
  - notes dirty-state and autosave behavior
- [x] Centralize route paths and API paths so components never hardcode `/admin/*`, ports, or OAuth URLs
- [x] Adopt React Query infrastructure: QueryClientProvider, api/client.js, queryKeys.js, endpoint modules
- [ ] Separate playlist concerns inside the frontend:
  - player lifecycle and progress sync
  - resume behavior
  - queue window and centering logic
  - notes dirty-state and autosave behavior
- [x] Add app-level error handling:
  - 404 page
  - 500/error boundary
  - auth-expired handling
  - consistent toast/error presentation

---

## Phase 5 — Testing, Quality Gates, and Developer Workflow

**Goal:** make refactors safe and repeatable.

- [ ] Replace server-spawning tests with FastAPI client-based testing
- [ ] Split tests into:
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
  - progress writes always targeting the correct active video
  - notes blur with unchanged content not triggering save toast
  - queue auto-centering and 3-card window behavior
- [ ] Add frontend coverage for critical flows:
  - login callback
  - Resources Drive connected state
  - staging queue actions
  - question/PYQ filtering and submission
  - reopening a playlist resumes the correct video and timestamp
  - `Next Video` shifts the queue and keeps the active card visible/centered when possible
  - marking one video watched does not clear another video’s watched state
- [ ] Add project tooling:
  - backend lint/format config
  - frontend lint cleanup
  - CI for backend tests, frontend build, and lint checks
- [x] Add architecture guardrails:
  - frontend raw API calls stay in endpoint modules
  - frontend endpoint modules are consumed through feature hooks
  - backend runtime layers do not use direct Mongo collection access
  - docs do not mention stale `server:app`

---

## Phase 6 — OCR Production Readiness

**Goal:** make OCR durable, isolated, and operationally safe.

- [ ] Replace FastAPI `BackgroundTasks` with a durable queue (`Redis` + `ARQ`/`RQ`)
- [ ] Make OCR jobs tenant-scoped end to end
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
  - Question Bank and PYQs at 50 per page
  - staging queue pagination or virtualization
- [ ] Make resource streaming truly streaming and avoid loading full Drive files into memory
- [ ] Add skeleton/loading states across major pages
- [ ] Optimize playlist queue behavior for long playlists with a fixed 3-card viewport and controlled navigation instead of raw scroll dependence
- [ ] Add global search:
  - backend `/api/search`
  - frontend Cmd/Ctrl+K overlay
  - questions, PYQs, resources, subjects, and topics
- [ ] Add optional Redis caching for dashboard and analytics after indexing is complete

---

## Phase 8 — Auth, Account, Deployment, and Compliance

**Goal:** make the product production-ready around accounts and deployment.

- [ ] Decide auth provider before email/password implementation:
  - recommended default: Supabase Auth or Auth0
- [ ] Add email/password flows only after provider selection:
  - signup
  - login
  - forgot/reset password
  - email verification
  - change password
- [ ] Keep Google login as a first-class auth option
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
