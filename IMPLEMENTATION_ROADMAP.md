# GATEPREP — Implementation Roadmap

## Summary

This roadmap replaces the older implementation roadmap as the source of truth.
Completed work still stands, but active work now prioritizes correctness, security,
maintainability, and then scale.

---

## Phase 0 — Baseline, Safety, and Repo Hygiene

**Goal:** make the repo trustworthy before larger refactors begin.

- [x] Ignore generated cache folders like `.vite/`
- [x] Keep large PDF source folders (`GATE_OVERFLOW/`, `UNACADEMY/`) out of git
- [ ] Create a backup branch before architecture refactor
- [ ] Remove generated cache folders from local worktree as needed
- [ ] Update docs to match live reality:
  - Vite is the active frontend toolchain
  - `VITE_BACKEND_URL` is canonical
  - local backend runs on `8001`
  - staging/import routes are `/api/data/*`
  - `/api/admin/*` is retired
- [x] Add `ARCHITECTURE.md` with the current domain map

---

## Phase 1 — P0 Stabilization and Broken Flow Fixes

**Goal:** remove current user-facing bugs and route/config drift before deeper work.

- [ ] Fix frontend route drift:
  - replace stale `/admin/*` frontend calls with `/data/*`
  - change OCR import success navigation from `/admin/staging` to `/data/staging`
- [ ] Fix Resources Drive false popup:
  - remove stale React-state dependency in `runSync`
  - scope `driveSyncNeeded` by `user_id`
  - do not set Drive sync needed on dev-login unless Drive is actually connected
- [ ] Remove remaining `difficulty` UI/state from Question Bank and Question Form
- [ ] Fix local config consistency:
  - `frontend/src/lib/api.js` fallback must match local backend `8001`
  - login UI must not mention port `8000`
- [ ] Fix hardcoded Google login config:
  - move frontend Google client ID and login redirect URI to Vite env vars
  - add missing backend env examples for login and YouTube redirect URIs
- [ ] Fix playlist correctness and resume flow:
  - stop stale player callbacks from writing progress to the wrong video after switching active videos
  - ensure playback/progress sync always targets the currently active `video_id`
  - reopen a playlist on the most recently in-progress or most recently watched video instead of always index `0`
  - restore saved `watch_time` when reopening a video
  - stop saved progress from being immediately overwritten by a fresh `0%` playback start
  - keep manually marked watched videos watched until the user explicitly unmarks them
- [ ] Fix playlist notes UX:
  - do not save notes on blur when content is unchanged
  - do not show `Notes saved` for no-op autosaves
  - keep autosave feedback quiet and stateful instead of toast-heavy
- [ ] Fix playlist queue behavior:
  - treat the queue as a controlled 3-card carousel, not a raw horizontal scroller
  - keep the active video card centered when possible
  - auto-shift the queue when `Next Video` activates a card outside the visible 3-card window
  - make manual scrolling snap back to valid 3-card windows
  - replace browser-like double-click queue shifting with deterministic one-step movement

---

## Phase 2 — Security and Multi-Tenant Isolation

**Goal:** close current security gaps before the large refactor.

- [ ] Make staging fully tenant-scoped:
  - store `user_id` on `import_jobs`, `staging_questions`, `topic_concepts`, and future `ocr_images`
  - filter list, delete, clear, approve-specific, and bulk-approve by `user_id`
  - prevent approving or deleting another user’s staging item
- [ ] Fix IDOR gaps:
  - `create_mistake` must fetch question with `user_id`
  - video progress must verify `video_id` ownership through the parent playlist before writes
  - video notes must verify `video_id` ownership through the parent playlist before reads and writes
  - analytics joins must avoid counting or exposing another user’s content
- [ ] Harden OAuth:
  - replace raw `user_id` OAuth state with random, expiring, session-bound state records
  - apply to Drive and YouTube OAuth
- [ ] Harden uploads and URL imports:
  - validate extension, MIME type, and PDF magic bytes
  - add OCR upload size limit
  - block localhost/private-network/non-HTTP(S) URL imports and oversized responses
- [ ] Harden production settings:
  - remove `tlsAllowInvalidCertificates=True` outside local development
  - use secure cookies in production
  - add CSP, HSTS, and audit logging for sensitive actions

---

## Phase 3 — Backend Full Refactor

**Goal:** move the backend to layered architecture with thin routes and central rules.

- [ ] Move backend into `app/` package architecture:
  - `app/main.py`
  - `app/api/v1/endpoints/`
  - `app/services/`
  - `app/repositories/`
  - `app/schemas/`
  - `app/core/`
- [ ] Split domains into explicit backend modules:
  - `auth`, `subjects`, `questions`, `pyqs`, `mistakes`, `analytics`, `playlists`, `resources`, `drive`, `youtube`, `ocr_import`, `staging`
- [ ] Make route handlers transport-only:
  - validate input
  - call services
  - return responses
- [ ] Move business rules into services:
  - latest-attempt accuracy
  - ownership checks
  - playlist resume-target selection based on `completed`, `watch_percentage`, `watch_time`, and `last_watched_at`
  - explicit watched/unwatched semantics instead of deriving all completion state from percentage alone
  - playlist delete cascade rules for videos, progress, and notes
  - Drive token refresh and sync
  - OCR job/staging lifecycle
  - question/PYQ approval flow
- [ ] Move all Mongo access into repositories with mandatory `user_id` filtering for user-owned collections
- [ ] Add playlist repository helpers for:
  - ownership-checked playlist/video lookups
  - latest watched or in-progress video resolution
  - playlist cleanup and video-note cascade deletion
- [ ] Remove duplicated helpers and models:
  - use one canonical `schemas`, `constants`, `time`, `id`, and response layer
  - replace route-local playlist progress schemas with canonical validated models
  - delete or migrate stale `backend/utils/*`, route-local schemas, and unused constants

---

## Phase 4 — Frontend Full Refactor

**Goal:** move from page-heavy orchestration to feature-oriented frontend architecture.

- [ ] Restructure frontend into:
  - `src/api/`
  - `src/features/auth`, `questions`, `pyqs`, `resources`, `playlists`, `ocr`, `analytics`, `subjects`, `mistakes`
  - `src/components/ui`
  - `src/components/domain`
  - `src/hooks`
  - `src/constants`
- [ ] Replace page-heavy state with reusable hooks:
  - `useDriveStatus`
  - `useResources`
  - `useResourceViewer`
  - `useStagingQueue`
  - `useQuestions`
  - `usePyqs`
  - `usePlaylists`
  - `usePlaylistDetail`
  - `useVideoProgress`
  - `useVideoNotes`
  - `usePlaylistQueue`
  - `useResumeVideo`
- [ ] Centralize route paths and API paths so components never hardcode `/admin/*`, ports, or OAuth URLs
- [ ] Adopt React Query consistently for server state and cache invalidation
- [ ] Separate playlist concerns inside the frontend:
  - player lifecycle and progress sync
  - resume behavior
  - queue window and centering logic
  - notes dirty-state and autosave behavior
- [ ] Add app-level error handling:
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

- [ ] Add DB indexes:
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
