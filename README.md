# GATE Study OS

> A high-performance, multi-tenant **Study Operating System** purpose-built for GATE Computer Science (CSE) preparation — Question Banks, PYQs, Mistake Lab, YouTube playlist tracking, PDF OCR ingestion, and a personal Google-Drive backed resource library, all wired to the official GATE CSE syllabus.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Shadcn UI](https://img.shields.io/badge/UI-shadcn%2Fui-000000)](https://ui.shadcn.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Table of Contents

- [Why this project](#why-this-project)
- [Product principles](#product-principles)
- [Feature tour](#feature-tour)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Data model](#data-model)
- [API surface](#api-surface)
- [Local development](#local-development)
- [Environment variables](#environment-variables)
- [Testing strategy](#testing-strategy)
- [Roadmap](#roadmap)
- [Engineering notes & deliberate decisions](#engineering-notes--deliberate-decisions)
- [Contributing](#contributing)
- [License](#license)

---

## Why this project

Most GATE prep platforms are content silos — they sell you their PDFs, their videos, their question banks. **GATE Study OS** flips that model on its head: it's an *operating system* you bring your own content to.

- **Your PYQs and questions** live in *your* topic taxonomy.
- **Your resources** (notes, books, cheat sheets) live in *your* Google Drive — we never hold them.
- **Your videos** are real YouTube playlists you already follow; we just track progress.
- **Your mistakes** are first-class artifacts you can revisit until they aren't mistakes anymore.
- **Your PDFs** are OCR-processed via Mistral AI into a structured question bank — verbatim, with topics and math intact.

The goal: a single, calm dashboard that tells you **what to study next** based on signal, not vibes.

---

## Product principles

1. **No vanity metrics.** We deliberately do **not** show a combined "subject completion %" — it's a lie that aggregates incomparable things. Topics expose only what is measurable: *Solved, Remaining, Accuracy*.
2. **Accuracy uses latest signal only.** Accuracy is derived ONLY from the latest attempt per question. History is preserved, but current proficiency is what matters. Re-solving a mistake fully overwrites the previous failure signal.
3. **Solutions are inline, never modal.** Reading a solution is part of solving — it shouldn't take you out of context.
4. **Playlists belong to subjects, not topics.** A real YouTube playlist crosses topic boundaries; forcing the user to lie about that produces bad data.
5. **The user owns the bytes.** Resources are pushed to the user's own Drive under `GATEPREP/{Type}/{Subject}/`. Disconnect anytime; your files keep working.
6. **No Admin Gatekeeping.** Every user is the super-user of their own data. The legacy admin role is retired; CRUD is available to everyone for their own personal bank.
7. **No default metadata pollution.** Questions ingested via OCR carry no hardcoded difficulty or source tag — the user declares source at upload time, and topic is auto-detected from the PDF's section headings.

---

## Feature tour

### Dashboard
A focused landing page showing **today's snapshot** — 8 high-level stat cards (Questions, PYQs, Videos, Accuracy, etc.) and a Subject HUD showing dual progress bars for QBank vs PYQ, color-coded by mastery.

### Subjects & Topics
- 12 subjects aligned to the **official GATE CSE syllabus**.
- Detailed topic-wise breakdown with rich stats and attempt feeds.
- Navigation is pre-filtered: clicking a topic opens the Question Bank filtered exactly to that area.

### Question Bank (MCQ / MSQ / NAT)
- Support for three question types: radio for MCQ, multi-select for MSQ, numeric input for NAT (with floating-point tolerance).
- **Advanced Filtering:** Instant filtering by Subject, Topic, and Type.
- **Inline solutions** revealed *after* submit — no modal, no context loss.
- **Math rendering:** Inline LaTeX/KaTeX via `mathFormat.jsx` — handles `$...$`, `\bar{X}`, `\oplus`, `\Sigma`, subscripts, superscripts, fractions.
- **Topic tag:** Each question carries a topic extracted from the PDF section heading (e.g. "Boolean Algebra", "Sequential Circuit") for filter-by-topic support.

### PYQs (Previous Year Questions)
- Tracked **separately** from the practice bank so accuracy is real and uncontaminated.
- **Year Filter:** Custom dropdown with a "shifted left" UI design, covering GATE years 2000 to 2026.

### Mistake Lab
Every incorrect attempt across Question Bank and PYQs lands here automatically.
- **Qualitative Tagging:** Categorize as Calculation Error, Conceptual Gap, etc.
- **Instant Management:** Deleting a mistake or re-solving it removes it from the lab.

### YouTube Playlists
- Import full video lists via YouTube Data API v3.
- Inline player using the **YouTube IFrame API** with live progress tracking (completed at 90% watch time).

### Resources (Google Drive Integration)
- Connect Drive via OAuth using the **`drive.file` scope**.
- **Inline PDF rendering** via `pdfjs-dist` on a `<canvas>` — bypasses cookie blocks.
- **Continuous multi-page scroll** with windowed rendering for 100MB+ files.
- **Resource Notes:** Free-form, auto-saving text notes per PDF.
- **Important Pages:** Flag, label, and jump to specific pages within mass textbooks.

### PDF OCR Ingestion (Mistral AI)
- Upload any GATE study material PDF via the **Import PDF** page.
- **Source tagging at upload time:** user specifies the publisher (e.g. "GO-PDFs", "MADE Easy") — no hardcoded defaults.
- **Mistral OCR pipeline** (`mistral-ocr-latest`) extracts the raw markdown page-by-page in 5-page chunks.
- **Structured extraction** (`mistral-large-latest`) converts markdown into typed Pydantic records — questions, solutions, concepts — with verbatim text, LaTeX-wrapped math, and section-based topic classification.
- **ID normalization:** `Q.1`, `Q1`, and `1` all resolve to the same key — questions and solutions from different sections of the PDF always merge into a single record instead of creating duplicates.
- **Staging Queue:** Live progress bar during ingestion, per-item Approve/Discard controls, bulk "Approve All 100% Matches", and "Clear All" for a clean re-run.
- **Dismissible error boxes:** Failed job errors show an ✕ button — dismissed permanently from both UI and DB.
- **Math rendering in staging:** All option text and question text is rendered through `formatMathText` so `$\bar{A}B + C$` displays as formatted math, not raw LaTeX.

---

## Architecture

```
                ┌──────────────────────────┐
                │  React 19 (CRA → Vite*)  │
                │  Tailwind + shadcn        │
                │  pdfjs-dist canvas        │
                │  mathFormat.jsx (KaTeX)   │
                └──────────┬───────────────┘
                           │ HTTPS (REACT_APP_BACKEND_URL)
                           │ /api/*
                ┌──────────▼───────────────┐
                │   FastAPI (Python)        │
                │   Motor (async MongoDB)   │
                │   Pydantic v2             │
                └──┬──────────┬────────────┘
                   │          │
                   │          ├──► Google Identity (Login)
                   │          ├──► Google Drive API (per-user OAuth)
                   │          ├──► YouTube Data API
                   │          ├──► Mistral AI (OCR + Chat Parse)
                   │          └──► Gemini API (Phase 7 - Upcoming)
                   │
            ┌──────▼──────┐
            │   MongoDB   │
            │ (multi-tenant
            │  by user_id)│
            └─────────────┘
```

> \* CRA → Vite migration is planned. See [Roadmap](#roadmap).

---

## Tech stack

**Frontend**
- React 19, react-router-dom 7, Tailwind CSS 3.4, Shadcn UI
- `pdfjs-dist` (custom canvas-based renderer)
- `axios` with interceptors for JWT/Cookie management
- `mathFormat.jsx` — custom math/LaTeX renderer (no KaTeX bundle overhead for simple expressions)

**Backend**
- FastAPI 0.136, Motor (Async MongoDB), Pydantic v2
- `httpx` for manual OAuth token exchange (no PKCE dependency)
- `StreamingResponse` for memory-efficient resource proxying
- `mistralai` SDK for OCR pipeline and structured chat parsing
- `pypdfium2` for PDF page slicing before Mistral upload

**Database**
- MongoDB (Indexing on `user_id` for multi-tenant isolation)
- Aggregation Pipelines for all high-volume analytics

---

## Repository layout

```
.
├── backend/
│   ├── routes/              # Modularized API endpoints
│   │   └── admin_staging.py # OCR import, staging CRUD, approve/discard
│   ├── scripts/
│   │   └── mistral_ocr.py   # MistralOCRPipeline — OCR + structured extraction
│   ├── tests/               # pytest suite
│   ├── config.py            # Pydantic Settings management
│   ├── server.py            # FastAPI entry point
│   └── shared.py            # Shared DB and Auth helpers
│
├── frontend/
│   ├── src/
│   │   ├── context/         # AuthProvider & State
│   │   ├── components/      # UI components (Viewer, Form, etc.)
│   │   │   └── QuestionViewer.jsx  # Renders question with math, tags, flags
│   │   ├── lib/
│   │   │   ├── api.js       # Axios instance
│   │   │   └── mathFormat.jsx  # Math/LaTeX rendering utility
│   │   └── pages/
│   │       ├── ImportPDF.jsx    # PDF upload with source field
│   │       └── StagingQueue.jsx # OCR review queue with live progress
│   └── public/
│
├── memory/
│   └── PRD.md               # Product Requirements
│
└── README.md
```

---

## Data model

| Collection            | Key fields                                                                                                        | Notes                                                        |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `users`               | `user_id, email, name, picture`                                                                                   | Identity via Google OAuth                                    |
| `subjects`            | `id, name, order`                                                                                                 | 12 official GATE subjects                                    |
| `questions`           | `question_id, subject_id, topic_id, topic, question_type, options, correct_answer, solution, source, tags`        | Practice collection. `difficulty` field intentionally absent |
| `pyqs`                | same shape as questions + `year, gate_set, gate_qnum`                                                             | PYQ-specific collection                                      |
| `question_attempts`   | `user_id, question_id, is_correct, attempted_at`                                                                  | Solving history                                              |
| `resources`           | `user_id, subject_id, title, drive_file_id`                                                                       | Metadata for Drive files                                     |
| `mistakes`            | `user_id, question_id, mistake_type, note`                                                                        | Capture of failures                                          |
| `staging_questions`   | `staging_id, subject_id, extracted_id, question_text, options, topic, question_type, correct_answer, solution_text, source, status` | OCR staging buffer. `status`: `READY`, `ORPHANED_QUESTION`, `ORPHANED_SOLUTION` |
| `import_jobs`         | `job_id, user_id, filename, engine, source, status, progress, total_pages, error`                                 | Tracks OCR pipeline runs. Dismissible via DELETE endpoint    |
| `topic_concepts`      | `concept_id, subject_id, title, content_markdown`                                                                 | Theory blocks extracted alongside questions                  |

---

## API surface

All routes under `/api`. Multi-tenant by `user_id`.

**Auth**
- `POST /api/auth/session` — Exchange Google code for session
- `POST /api/auth/dev-login` — Development bypass (Demo Student)

**Analytics**
- `GET  /api/analytics/subject/{id}` — DB-level aggregate stats

**Questions & PYQs**
- `GET  /api/questions` — Paginated questions with joined attempts
- `POST /api/questions` — Add question
- `GET  /api/pyqs` — PYQ bank

**Resources**
- `GET  /api/resources/{id}/stream` — Chunked Drive proxy stream

**Playlists**
- `POST /api/playlists/import` — YouTube Data API ingestion

**PDF OCR Pipeline (Admin)**
- `POST /api/admin/import/pdf` — Upload PDF, specify engine + source, kick off background OCR job
- `GET  /api/admin/import/jobs` — List recent import jobs with progress
- `DELETE /api/admin/import/jobs/{job_id}` — Dismiss (delete) a completed/failed job record
- `GET  /api/admin/staging` — List all staging queue items
- `DELETE /api/admin/staging/{staging_id}` — Discard a single staging item
- `DELETE /api/admin/staging` — Clear entire staging queue (fresh-start before re-ingestion)
- `POST /api/admin/staging/approve-specific` — Approve a single item (force-approve orphans)
- `POST /api/admin/staging/bulk-approve` — Approve all READY items in one shot

---

## Local development

### Prerequisites
- Python 3.12+ (Standard Windows distribution)
- Node.js 20+, npm
- MongoDB Atlas cluster
- Mistral AI API key (`MISTRAL_API_KEY` in `backend/.env`)

### Quick start

```bash
# 1. Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python seed.py   # Populate syllabus subjects
uvicorn server:app --reload --port 8000

# 2. Frontend
cd ../frontend
npm install --legacy-peer-deps
npm start        # Runs on http://localhost:3000
```

> **Note on frontend startup time:** The project currently uses Create React App (CRA) which compiles the entire bundle on every cold start (~30–60 seconds). A migration to **Vite** is planned — it will reduce cold-start time to under 1 second. See [Roadmap](#roadmap).

---

## Environment variables

### `backend/.env`

| Variable | Description |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name (e.g. `gate_study_os`) |
| `JWT_SECRET` | Random string for signing sessions |
| `GOOGLE_DRIVE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_DRIVE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_LOGIN_REDIRECT_URI` | e.g. `http://localhost:3000/auth/callback` |
| `GOOGLE_DRIVE_REDIRECT_URI` | e.g. `http://localhost:8000/api/drive/callback` |
| `MISTRAL_API_KEY` | Mistral AI API key — required for PDF OCR pipeline |
| `FRONTEND_URL` | e.g. `http://localhost:3000` — used for CORS |

---

## Testing strategy

- **Backend:** `pytest` suite in `backend/tests/`. Run with `pytest -v`.
- **Manual Logic:** `self_test_logic.py` for verifying aggregation pipelines.
- **Tokens:** `create_test_tokens.py` for injecting sessions into local DB.
- **OCR Pipeline:** Trigger via Import PDF page, verify Staging Queue item count matches expected question count in the PDF.

---

## Roadmap

### ✅ Completed

- **Phase 1 — MVP Hardening:** MongoDB aggregation pipelines, StreamingResponse, manual OAuth, de-branding.
- **Phase 2 — User Autonomy:** Admin retirement, year dropdown, dev-bypass login, multi-tenant indexing.
- **Phase 5 — PDF OCR Pipeline (Core):**
  - Mistral AI OCR + structured extraction via `mistral-large-latest`.
  - Staging queue with live progress bar, per-item Approve/Discard, bulk approve.
  - Source field on Import page (user-defined, no default).
  - Topic auto-detection from PDF section headings.
  - ID normalization (`Q.1` / `1` → same record, no duplicates).
  - Math rendering in staging queue and question viewer via `mathFormat.jsx`.
  - Dismissible error boxes on failed jobs.
  - Clear All staging button for clean re-ingestion.
  - Removed hardcoded `difficulty` and `source` defaults from all approve flows.

---

### 🔴 P0 — Active

- **OCR Image Extraction:** Circuit diagrams currently render as `📐 [Figure Description]` placeholders because Mistral's structured extraction pass does not return base64 image data. Solution: capture base64 images from the raw OCR response and store them separately (MongoDB GridFS or object storage), then serve via a `/api/images/{id}` endpoint.
- **Dismiss failed job errors from DB:** `DELETE /api/admin/import/jobs/{job_id}` endpoint is implemented — frontend ✕ button calls it on click.

---

### 🟡 P1 — Next

- **Vite Migration:** Replace Create React App with Vite. Cold-start drops from ~50s to <1s. HMR becomes instant. Build output is significantly smaller. Steps: `npm create vite@latest`, migrate `craco.config.js` aliases to `vite.config.js`, update env prefix from `REACT_APP_` to `VITE_`.
- **Full KaTeX Integration:** Replace `mathFormat.jsx` custom renderer with the official KaTeX library for 100% LaTeX coverage including `\int`, `\lim`, matrices, and multi-line equations.
- **Pagination on Question Bank/PYQs:** Current implementation loads all questions. Add cursor-based pagination at 50 per page.
- **Global Search (Cmd+K):** Unified search bar across Subjects, Topics, Resources, and Questions using MongoDB text indexes.
- **MongoDB Indexes:** Add compound indexes on `(subject_id, topic)` and `(user_id, status)` for staging and question collections to avoid collection scans at scale.

---

### 🟢 P2 — Later

- **SM-2 Spaced Repetition:** Implement the SuperMemo-2 scheduling algorithm in Mistake Lab — re-order by review date, track ease factor per question.
- **Mock Test Mode:** Timed GATE-style simulation with 65 questions, 3 hours, negative marking, auto-submit.
- **PWA / Offline Support:** Service worker for the custom PDF canvas reader so it works without a network connection.
- **Backend Route Splitting:** `server.py` is currently monolithic. Split into `routes/` sub-modules per domain once it crosses ~2k LOC.
- **Redis Caching:** Cache aggregation pipeline results (dashboard stats, subject analytics) in Redis with a 5-minute TTL to reduce MongoDB load under concurrent users.

---

### 💭 Exploratory Backlog

- AI conversational tutor (Chat with your notes via Gemini).
- Streak and Daily Goal HUD.
- Calibration diagnostic quiz on boarding.
- Multi-user collaborative question banks.

---

## Engineering notes & deliberate decisions

1. **DB-Level Aggregation:** We use MongoDB `$lookup` and `$group` for all analytics. This ensures the app stays "instant" even with 5,000+ questions.
2. **Manual OAuth:** We bypass standard libraries for token exchange to avoid PKCE/Verifier conflicts between frontend and backend.
3. **Canvas PDF Engine:** Custom rendering via `pdfjs-dist` ensures the reader works in privacy-hardened browsers.
4. **Admin Role Retired:** To fulfill the "Personal Study OS" vision, every user has full authority over their own data.
5. **No `difficulty` field:** Difficulty is subjective and varies by student background. It is intentionally absent from the data model. Users can tag difficulty themselves via the `tags` array if needed.
6. **OCR reads env directly:** `mistral_ocr.py` reads `MISTRAL_API_KEY` via `os.environ.get()` instead of the Pydantic `settings` object. This is deliberate — background tasks spawned by FastAPI's `BackgroundTasks` run in a worker context where the `settings` singleton may not be fully initialized, causing `NameError`. Reading env directly is safe and deterministic.
7. **ID normalization in OCR:** A GATE study PDF typically has questions numbered `Q.1`–`Q.65` in one section and solutions numbered `1`–`65` in another. Without normalization these are treated as 130 separate records. `normalize_id()` strips the `Q.` prefix so both always resolve to the same staging document.
8. **5-page OCR chunks:** The pipeline slices the PDF into 5-page chunks before uploading to Mistral. This keeps individual API payloads small, enables granular progress reporting, and makes partial failures recoverable (a bad chunk doesn't kill the whole job).

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for conventions, branching strategy, and PR checklist.

---

## License

MIT License. Built for aspirants who believe **study tools should serve you, not silo you.**
