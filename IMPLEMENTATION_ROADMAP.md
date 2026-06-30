# GATEPREP — Implementation Roadmap

## Phase 0 — Git Sync

**Goal:** Clean up repo, push current state, create backup.

- [ ] Delete debug scripts:
  - `backend/check_db2.py`
  - `backend/check_jobs.py`
  - `backend/check_q65.py`
  - `backend/clear_db.py`
  - `backend/fix_answers.py`
  - `backend/scratch/` (entire folder)
- [ ] Move `backend/test_short.pdf` → `backend/tests/fixtures/`
- [ ] Run `git status` — review all modified and untracked files
- [ ] Verify `backend/.env` is NOT tracked in git (`git ls-files | grep .env`)
- [ ] Create/update `.gitignore` if needed
- [ ] Stage appropriate files, commit, push to `origin/main`
- [ ] Create backup branch: `git branch backup-before-refactor`

---

## Phase 1 — Quick Wins + Low-Risk Structure Fixes

**Goal:** Faster dev experience, remove dead branding, clean up easy structural issues.

### 1.1 Vite Migration
- [x] Install `vite` + `@vitejs/plugin-react`
- [x] Create `vite.config.js` with React plugin and `@` alias
- [x] Move `index.html` to root, update for Vite (script module, no `%PUBLIC_URL%`)
- [x] Rename `src/index.js` → `src/index.jsx`, `src/App.js` → `src/App.jsx`
- [x] Replace `REACT_APP_*` env vars with `VITE_*`
- [x] Update `package.json` scripts: `craco start/build` → `vite`/`vite build`
- [x] Remove `craco.config.js`, `react-scripts`, `@craco/craco`, `cra-template`
- [x] Remove `public/index.html` (moved to root)
- [x] **Build verified — 6s vs ~50s previously** ✅
- [ ] Test: Drive viewer, PDF viewer, YouTube player, OCR staging queue after migration
- [ ] Update `SELF_HOSTING.md` build settings if needed

### 1.2 Rebranding
- [ ] `README.md` — title + body references
- [ ] `PRD.md` — title
- [ ] `IMPLEMENTATION_PLAN.md` — title
- [ ] `OCR_PIPELINE.md` — title
- [ ] `CONTRIBUTING.md` — title
- [ ] `SELF_HOSTING.md` — all "GATE Study OS" references
- [ ] `backend/server.py` — docstring
- [ ] `backend/seed.py` — docstring
- [ ] `backend/migrations.py` — docstring
- [ ] `backend/tests/test_gate_os_backend.py` — docstring + rename file to `test_gateprep_backend.py`
- [ ] Rename MongoDB DB name `gate_study_os` → `gateprep` (update `.env.example` if needed)
- [ ] Keep Drive folder name `GATEPREP/` as-is

### 1.3 Remove Admin Everywhere
- [ ] Delete `frontend/src/pages/Admin.jsx`
- [ ] Remove `is_admin` field from users schema and all code references
- [ ] Remove `ADMIN_EMAILS` from `config.py` and `.env.example`
- [ ] Remove `get_admin_user()` dependency and all admin-only endpoints in `practice.py`:
  - `POST /api/admin/questions`
  - `DELETE /api/admin/questions/{id}`
  - `POST /api/admin/pyqs`
  - `DELETE /api/admin/pyqs/{id}`
  - `GET /api/admin/users`
- [ ] Rename `/api/admin/*` routes → `/api/data/*` or `/api/import/*`:
  - `admin_staging.py` route prefix from `/admin` → `/data`
  - Update frontend `Layout.jsx` nav links
  - Update route paths in `App.js`

### 1.4 Remove Difficulty Everywhere
- [ ] Remove `difficulty` from `seed.py` sample data
- [ ] Remove `difficulty` default from `QuestionIn` Pydantic model
- [ ] Remove `difficulty` from `QuestionPatch` model
- [ ] Remove `difficulty` filter parameter from `list_questions` and `list_pyqs`
- [ ] Remove `difficulty` display from `QuestionViewer.jsx` and any other components
- [ ] Remove `difficulty` from `QuestionForm.jsx` if present

### 1.5 Delete Dead Code
- [ ] `backend/scripts/import_go_pdfs.py`
- [ ] `backend/scripts/parse_llama.py`
- [ ] `backend/scripts/parse_unacademy.py`
- [ ] Clean up `admin_staging.py` dead imports:
  - Remove `PDFOrchestrator` import
  - Remove `parse_with_llama` import
  - Remove `run_llama_parser_background()` function
  - Remove `run_ocr_pipeline_background()` function

### 1.6 Low-Risk Backend Restructure
- [ ] Add `__init__.py` to `backend/routes/`, `backend/scripts/`, `backend/tests/`
- [ ] Split `routes/core.py`:
  - `routes/auth.py` — dev-login, session, logout, me
  - `routes/subjects.py` — subjects, topics CRUD
- [ ] Extract Pydantic schemas to `backend/schemas.py`:
  - `AttemptIn`, `NotesIn`, `QuestionIn`, `QuestionPatch`, `PYQIn`, `FlagIn`, `MistakeIn`
  - `ApproveSpecificRequest`
  - `PlaylistImportIn`, `VideoProgressIn`
  - `ResourceIn`, `ResourceNotesIn`, `TogglePageIn`, `PageLabelIn`
- [ ] Extract string constants to `backend/constants.py`:
  - `QUESTION_TYPES = ["MCQ", "MSQ", "NAT"]`
  - `FLAG_TYPES = ["review", "important"]`
  - `MISTAKE_TYPES = ["Conceptual Gap", "Calculation Error", "Question Misread", "Silly Mistake"]`
- [ ] Move utility helpers from `shared.py`:
  - `err()` / `ok()` → `backend/utils/response.py`
  - `new_id()` → `backend/utils/id.py`
  - `now_utc()`, `iso()` → `backend/utils/time.py`
  - `async_get`, `async_post` → `backend/utils/http.py`

### 1.7 Low-Risk Frontend Cleanup
- [ ] Extract `FilterPills` component from `QuestionBank.jsx` / `PYQs.jsx` → `components/common/FilterPills.jsx`
- [ ] Move `lib/api.js` → `api/client.js`
- [ ] Create `frontend/src/components/common/` directory

---

## Phase 2 — Security Hardening

- [ ] Lock down CORS: `allow_origins=["*"]` → specific production domain list
- [ ] Add rate limiting middleware (slowapi or fastapi-limiter):
  - Login: 5 attempts/15 min per IP
  - General API: 100 requests/min per user
  - File upload: 10 requests/min per user
- [ ] Fix IDOR on staging endpoints:
  - `GET /api/data/staging` — filter by `user_id`
  - `DELETE /api/data/staging` — filter by `user_id`
  - `DELETE /api/data/staging/{id}` — verify ownership
  - `POST /api/data/staging/approve-specific` — verify ownership
- [ ] Add global exception handler with `@app.exception_handler(Exception)`
- [ ] Set `secure=True`, `SameSite=Strict` on session cookies in production
- [ ] Remove `tlsAllowInvalidCertificates=True` for production MongoDB
- [ ] Guard `/api/auth/dev-login` behind `if not PRODUCTION` env check
- [ ] Add security headers middleware:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000`
  - `Content-Security-Policy`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] Secure file uploads:
  - Validate PDF magic bytes (`%PDF` header)
  - Validate MIME type on backend
  - Enforce extension whitelist (`.pdf` only)
  - 50MB size limit on PDF import endpoint
- [ ] Add global request payload size limit middleware
- [ ] Sanitize MongoDB operators: strip `$` and `.` from user input strings
- [ ] Add HTTPS redirect middleware for production
- [ ] Invalidate all sessions when user changes password
- [ ] Add audit log for sensitive actions:
  - Logins (success/failure)
  - Password changes
  - Drive connect/disconnect
  - Question/PYQ deletes
  - Import job starts/completions
- [ ] Validate OAuth `state` parameter in Google login callback
- [ ] Scan repo for leaked secrets (PostHog key in `index.html`, any other hardcoded tokens)
- [ ] Rotate any exposed secrets

---

## Phase 3 — YouTube OAuth

- [ ] Add `youtube.readonly` OAuth scope to Google OAuth flow
- [ ] Store per-user YouTube access/refresh tokens in `youtube_credentials` collection
- [ ] Create `GET /api/youtube/auth` endpoint — returns auth URL
- [ ] Create `GET /api/youtube/callback` — handles OAuth callback, stores tokens
- [ ] Create `GET /api/youtube/status` — check if user has YouTube connected
- [ ] Create `POST /api/youtube/disconnect` — revoke tokens
- [ ] Update playlist import to use per-user YouTube token instead of shared API key
- [ ] Remove `YOUTUBE_API_KEY` from `config.py` and `.env.example`
- [ ] Update frontend Settings page with YouTube connect/disconnect UI
- [ ] Update `Playlists.jsx` to use OAuth-aware API calls

---

## Phase 4 — Authentication

- [ ] Integrate Supabase Auth or Auth0 (recommended over DIY)
- [ ] Add email/password signup endpoint
- [ ] Add email/password login endpoint
- [ ] Add password change endpoint
- [ ] Add forgot-password endpoint (sends reset email, token expires in 30 min)
- [ ] Add reset-password endpoint (consumes token, 30 min expiry)
- [ ] Add email verification flow (verification token expires in 30 min)
- [ ] Password complexity rules: min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special
- [ ] Login rate limiting: max 5 attempts per IP per 15 minutes
- [ ] Account lockout after 10 failed attempts (30 min lock)
- [ ] Update `AuthContext.jsx` to support both Google OAuth and email/password
- [ ] Update `Login.jsx` — add email/password form alongside Google button
- [ ] Create `Signup.jsx` — registration page
- [ ] Create `ForgotPassword.jsx` / `ResetPassword.jsx`
- [ ] Update `Settings.jsx` — add "Change Password" section, "Connected Accounts" section
- [ ] Add form validation with zod + react-hook-form (already in deps)

---

## Phase 5 — Full Restructure

### Backend: Move to `app/` Package with Layered Architecture

- [ ] Create directory structure:
  ```
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── constants.py
  │   ├── dependencies.py
  │   ├── exceptions.py
  │   ├── logging_config.py
  │   ├── middleware.py
  │   ├── db/
  │   │   ├── __init__.py
  │   │   └── session.py
  │   ├── schemas/
  │   │   ├── __init__.py
  │   │   └── *.py
  │   ├── api/v1/endpoints/
  │   │   ├── __init__.py
  │   │   └── *.py
  │   ├── services/
  │   │   ├── __init__.py
  │   │   └── *.py
  │   ├── repositories/
  │   │   ├── __init__.py
  │   │   └── *.py
  │   └── utils/
  │       ├── __init__.py
  │       └── *.py
  ├── scripts/
  ├── tests/
  ├── pyproject.toml
  └── pytest.ini
  ```
- [ ] Move `server.py` → `app/main.py` (clean entry point, no routes)
- [ ] Move `config.py` → `app/config.py`
- [ ] Move all routes to `app/api/v1/endpoints/`
- [ ] Extract business logic into `app/services/`:
  - `auth_service.py`
  - `question_service.py`
  - `staging_service.py`
  - `drive_service.py`
  - `youtube_service.py`
  - `ocr_service.py`
- [ ] Extract data access into `app/repositories/`:
  - `user_repo.py`
  - `question_repo.py`
  - `staging_repo.py`
  - `pyq_repo.py`
  - `playlist_repo.py`
- [ ] Add `pyproject.toml` with project metadata, ruff config, pytest config
- [ ] Add `pytest.ini`
- [ ] Add linting config (ruff or black)

### Frontend: Feature-Based Folders + Domain API Modules

- [ ] Restructure to:
  ```
  frontend/src/
  ├── main.jsx
  ├── App.jsx
  ├── routes.jsx
  ├── api/
  │   ├── client.js
  │   ├── auth.api.js
  │   ├── questions.api.js
  │   ├── pyqs.api.js
  │   ├── playlists.api.js
  │   ├── resources.api.js
  │   └── staging.api.js
  ├── features/
  │   ├── auth/
  │   ├── questions/
  │   ├── pyqs/
  │   ├── ocr/
  │   ├── resources/
  │   ├── playlists/
  │   └── analytics/
  ├── components/
  │   ├── ui/
  │   ├── common/
  │   └── domain/
  ├── hooks/
  ├── context/
  ├── lib/
  ├── constants/
  └── styles/
  ```
- [ ] Move existing pages into `features/` folders with their related components
- [ ] Create domain API modules in `api/`
- [ ] Add React Query custom hooks per feature
- [ ] Add error boundary component
- [ ] Add 404 and 500 error pages

### Testing Improvements
- [ ] Replace `subprocess.Popen` + `requests` with FastAPI `TestClient`
- [ ] Separate `tests/unit/` and `tests/integration/`
- [ ] Add fixtures for DB, auth tokens, mock data
- [ ] Add basic unit tests for key services

---

## Phase 6 — UX & Performance

- [ ] Skeleton loading states on all pages (Dashboard, Subjects, QuestionBank, PYQs, etc.)
- [ ] Database indexes:
  - `question_attempts`: `(user_id, question_id)`
  - `pyq_attempts`: `(user_id, pyq_id)`
  - `staging_questions`: `(user_id, status)`
  - `questions`: compound `(subject_id, topic)`
  - `pyqs`: compound `(subject_id, topic)`
- [ ] Pagination on Question Bank / PYQs (cursor-based, 50 per page)
- [ ] Redis caching for dashboard + subject analytics (5-min TTL, invalidate on new attempt)

---

## Phase 7 — OCR Production Readiness

- [ ] Replace `BackgroundTasks` with durable message queue (ARQ + Redis)
- [ ] OCR image extraction:
  - Capture `page.images` base64 from Mistral raw OCR response
  - Store in `ocr_images` collection: `{ image_id, job_id, page, base64, mime_type }`
  - Replace `img-N.jpeg` references in staging docs with `image_id`
  - Add `GET /api/data/ocr-images/{image_id}` endpoint
  - Update `mathFormat.jsx` to render `<img>` tags
- [ ] Per-user Mistral OCR page cap (e.g., 50 pages/user/month)

---

## Phase 8 — Scalability Infrastructure

- [ ] Load balancer (Nginx / Render / Cloudflare)
- [ ] MongoDB Atlas replicaset for HA
- [ ] CDN for frontend static assets
- [ ] API gateway at proxy level (Cloudflare / Kong)
- [ ] Deeper health checks: DB connectivity, API key validity

---

## Phase 9 — Legal & Marketing

- [ ] Privacy Policy page
- [ ] Terms & Conditions page
- [ ] Cookie consent banner (GDPR compliant)
- [ ] Make PostHog session recording conditional on consent
- [ ] `robots.txt` + `sitemap.xml`
- [ ] Open Graph meta tags
- [ ] Contact/support email link in UI
- [ ] Bug report button/form
- [ ] Submit to Google Search Console

---

## Design Principles (Keep in Mind)

- **CAP theorem**: MongoDB prioritizes AP by default. Acceptable for this use case. Revisit only if strong consistency becomes critical.
- **Consistent hashing**: Not needed until MongoDB sharding is required (100k+ users / 1M+ documents).
- **API Versioning**: `api/v1/...` prefix. Add when splitting into multiple backend services.
