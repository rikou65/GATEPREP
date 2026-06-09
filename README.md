# GATE Study OS

> A multi-tenant **Study Operating System** purpose-built for GATE Computer Science (CSE) preparation — Question Banks, PYQs, Mistake Lab, YouTube playlist tracking, and a personal Google-Drive backed resource library, all wired to the official GATE CSE syllabus.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
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

Most GATE prep platforms are content silos — they sell you their PDFs, their videos, their question banks. **GATE Study OS** flips that model on its head: it’s an *operating system* you bring your own content to.

- Your **PYQs and questions** live in *your* topic taxonomy.
- Your **resources** (notes, books, cheat sheets) live in *your* Google Drive — we never hold them.
- Your **videos** are real YouTube playlists you already follow; we just track progress.
- Your **mistakes** are first-class artifacts you can revisit until they aren’t mistakes anymore.

The goal: a single, calm dashboard that tells you **what to study next** based on signal, not vibes.

---

## Product principles

1. **No vanity metrics.** We deliberately do **not** show a combined "subject completion %" — it’s a lie that aggregates incomparable things. Topics expose only what is measurable: *Solved, Remaining, Accuracy*.
2. **Solutions are inline, never modal.** Reading a solution is part of solving — it shouldn’t take you out of context.
3. **Playlists belong to subjects, not topics.** A real YouTube playlist crosses topic boundaries; forcing the user to lie about that produces bad data.
4. **The user owns the bytes.** Resources are pushed to the user’s own Drive under `GATEPREP/{Type}/{Subject}/`. Disconnect anytime; your files keep working.
5. **Multi-tenant by design.** Every read and write is scoped to `user_id`. No global question pools, no shared progress.

---

## Feature tour

### Dashboard
A focused landing page showing **today's snapshot** — recent attempts, accuracy trend, weakest topics, latest mistakes, and continue-watching cards from in-progress playlists.

### Subjects & Topics
- 12 subjects aligned to the **official GATE CSE syllabus** (Engineering Mathematics, Discrete Math, DSA, Algorithms, TOC, Compilers, OS, DBMS, CN, COA, Digital Logic, Aptitude).
- Each topic page shows **Solved / Remaining / Accuracy** and a chronological feed of attempts.

### Question Bank (MCQ / MSQ / NAT)
- Three question types with proper UX semantics: radio for MCQ, multi-select for MSQ, numeric input for NAT (with tolerance range).
- **Inline solutions** revealed *after* submit — no modal, no context loss.
- Automatic logging into `question_attempts` for analytics.

### PYQs (Previous Year Questions)
- Tracked **separately** from the practice bank so accuracy on PYQs is a real, uncontaminated signal.
- Filter by year, subject, topic.

### Mistake Lab
Every incorrect attempt across Question Bank and PYQs lands here automatically. Re-attempt a mistake → it leaves the lab. Simple, sharp, effective.

### YouTube Playlists
- Paste any public YouTube playlist URL → we import the full video list via the YouTube Data API.
- Playlists are grouped by **subject**.
- Inline player using the **YouTube IFrame API** with live progress tracking (`watch_percentage`, `completed`) auto-saved to `video_progress`.
- “Continue watching” surfaced on the dashboard.

### Resources (Google Drive Integration)
- Connect Drive via OAuth using the **`drive.file` scope** — we can only see files *we* created on your behalf. Your personal files remain invisible to us.
- We auto-provision a `GATEPREP/{PDF|Notes|Other}/{Subject}/` hierarchy in your Drive.
- Uploads stream through the backend → pushed to Drive → metadata stored in MongoDB.
- **Inline PDF rendering** via `pdfjs-dist` on a `<canvas>` — bypasses Brave/Chrome third-party-cookie blocks that break Google’s native Drive iframe viewer.
- Sticky toolbar with **page jump**, in-session blob cache (no re-downloads), Portal-rendered modal (no sidebar overlap).

### Admin Portal
- CRUD for Subjects, Topics, Questions, PYQs.
- Role-gated (`is_admin` on the user document).
- The launching pad for the upcoming **OCR Review Queue** (Phase 5).

### Authentication
- **Emergent-managed Google Auth** for user identity (one-click sign-in, JWT sessions).
- A **separate Google OAuth client** for Drive — keeping identity and storage authorisation cleanly decoupled.

---

## Architecture

```
                ┌──────────────────────┐
                │  React 19 + Vite/CRA │
                │  Tailwind + shadcn   │
                │  pdfjs-dist canvas   │
                └──────────┬───────────┘
                           │ HTTPS (REACT_APP_BACKEND_URL)
                           │ /api/*
                ┌──────────▼───────────┐
                │   FastAPI (Python)   │
                │   Motor (async)      │
                │   Pydantic v2        │
                └──┬──────────┬────────┘
                   │          │
                   │          ├──► Google Drive API (per-user OAuth)
                   │          ├──► YouTube Data API
                   │          └──► Emergent LLM key (Gemini — upcoming)
                   │
            ┌──────▼──────┐
            │   MongoDB   │
            │ (multi-tenant
            │  by user_id)│
            └─────────────┘
```

**Why FastAPI + MongoDB?** Original stack was Go/Postgres, switched to FastAPI/MongoDB for environment portability and richer Python OCR/LLM ecosystem. Pydantic v2 gives us PostgreSQL-grade schema validation without the migration overhead.

---

## Tech stack

**Frontend**
- React 19, React Router 7, Tailwind 3.4, Shadcn UI, Radix primitives
- `framer-motion`, `recharts`, `lucide-react`
- `pdfjs-dist` (canvas-based PDF viewer)
- `axios` with auth interceptors, `swr` for data fetching

**Backend**
- FastAPI 0.110, Uvicorn, Pydantic v2
- Motor 3 (async MongoDB driver)
- `google-api-python-client`, `google-auth-oauthlib` (Drive OAuth)
- `emergentintegrations` (Universal Emergent LLM key — Gemini/OpenAI/Anthropic)
- `pytest` for backend unit/integration tests

**Database**
- MongoDB (collections per entity, scoped on `user_id`)

**Auth**
- Emergent-managed Google Auth → JWT
- Independent Google OAuth client with `drive.file` scope

---

## Repository layout

```
.
├── backend/
│   ├── server.py                       # FastAPI app — routes, schemas, helpers (~1.4k LOC)
│   ├── requirements.txt
│   ├── .env                            # MONGO_URL, DB_NAME, Google client creds, JWT secret
│   └── tests/
│       └── test_gate_os_backend.py     # pytest suite
│
├── frontend/
│   ├── src/
│   │   ├── App.js, index.js, index.css
│   │   ├── context/AuthContext.jsx     # JWT/session context
│   │   ├── lib/api.js                  # Axios instance + interceptors
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── PdfCanvasViewer.jsx     # Custom canvas PDF renderer
│   │   │   ├── QuestionViewer.jsx
│   │   │   └── ui/                     # shadcn primitives
│   │   └── pages/
│   │       ├── Login.jsx, AuthCallback.jsx
│   │       ├── Dashboard.jsx, Analytics.jsx
│   │       ├── Subjects.jsx, SubjectDetail.jsx, TopicDetail.jsx
│   │       ├── QuestionBank.jsx, PYQs.jsx, MistakeLab.jsx
│   │       ├── Playlists.jsx, PlaylistDetail.jsx
│   │       ├── Resources.jsx, Settings.jsx
│   │       └── Admin.jsx
│   ├── package.json, tailwind.config.js, craco.config.js
│   └── .env                            # REACT_APP_BACKEND_URL
│
├── memory/
│   ├── PRD.md                          # Living product requirements
│   └── test_credentials.md             # Seeded test accounts
│
├── test_reports/
│   └── iteration_*.json                # Testing-agent run reports
│
└── README.md
```

---

## Data model

Only the fields that matter; timestamps and audit columns elided.

| Collection            | Key fields                                                                                          | Notes                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `users`               | `id, email, name, picture, is_admin`                                                                | Identity via Emergent Google Auth                      |
| `subjects`            | `id, name`                                                                                          | 12 fixed GATE CSE subjects                             |
| `topics`              | `id, subject_id, name`                                                                              | Official syllabus hierarchy                            |
| `questions`           | `id, subject_id, topic_id, question_text, type, options, correct_answer, solution, difficulty`     | `type ∈ {MCQ, MSQ, NAT}`                               |
| `pyqs`                | same shape as `questions` + `year`                                                                  | Tracked **separately** for clean PYQ accuracy          |
| `question_attempts`   | `user_id, question_id, is_correct, time_taken, submitted_answer`                                    | Multi-tenant feed                                      |
| `pyq_attempts`        | `user_id, pyq_id, is_correct, time_taken, submitted_answer`                                         | Mirror of attempts for PYQs                            |
| `playlists`           | `user_id, subject_id, youtube_playlist_id, title, thumbnail`                                        | Grouped by subject                                     |
| `videos`              | `playlist_id, youtube_video_id, title, position, duration`                                          | Imported via YouTube Data API                          |
| `video_progress`      | `user_id, video_id, watch_percentage, completed, last_position`                                     | Live updates from IFrame API                           |
| `resources`           | `user_id, subject_id, title, drive_file_id, view_url, mime_type, size`                              | Files live in user’s Drive; we store metadata only     |
| `google_drive_accounts` | `user_id, refresh_token, root_folder_id, scope`                                                   | One row per connected Drive account                    |
| `mistakes`            | (logical view from `question_attempts` + `pyq_attempts` where `is_correct=false`)                   | No physical collection — derived                       |

---

## API surface

Routes are mounted under `/api`. Auth required unless noted.

### Auth
- `GET  /api/auth/google/login` → returns Google OAuth URL (identity)
- `GET  /api/auth/google/callback` → exchanges code, mints JWT
- `GET  /api/auth/me` → current user

### Subjects / Topics
- `GET  /api/subjects`
- `GET  /api/subjects/{id}/topics`
- `GET  /api/topics/{id}/stats` → `{solved, remaining, accuracy}`

### Question Bank
- `GET  /api/questions?subject_id=&topic_id=&type=`
- `POST /api/questions/{id}/attempt` → records attempt, returns correctness + solution

### PYQs
- `GET  /api/pyqs?year=&subject_id=&topic_id=`
- `POST /api/pyqs/{id}/attempt`

### Mistake Lab
- `GET  /api/mistakes` → unresolved mistakes (questions + PYQs)
- `POST /api/mistakes/{attempt_id}/retry`

### Playlists
- `POST /api/playlists/import` → `{youtube_playlist_url, subject_id}`
- `GET  /api/playlists?subject_id=`
- `GET  /api/playlists/{id}/videos`
- `PUT  /api/videos/{id}/progress` → `{watch_percentage, completed}`

### Resources (Google Drive)
- `GET  /api/drive/connect` → returns Drive OAuth URL
- `GET  /api/drive/callback` → completes Drive OAuth, stores refresh token
- `POST /api/drive/disconnect`
- `POST /api/resources/upload` *(multipart)* → uploads to Drive, persists metadata
- `GET  /api/resources?subject_id=`
- `GET  /api/resources/{id}/stream` → streams bytes through backend (Brave/Chrome cookie-block workaround)
- `DELETE /api/resources/{id}`

### Admin *(requires `is_admin`)*
- `POST /api/admin/questions`, `PUT /api/admin/questions/{id}`, `DELETE /api/admin/questions/{id}`
- Mirror for `/api/admin/pyqs/...`
- `POST /api/admin/seed` *(dev only)*

---

## Local development

### Prerequisites
- Python **3.11+**
- Node **20+**, Yarn (do **not** use npm — breaking changes in CRA toolchain)
- MongoDB running locally or a connection string
- Google Cloud project with:
  - OAuth client (web) → for Drive
  - YouTube Data API enabled

### Quick start

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env       # fill in MONGO_URL, DB_NAME, GOOGLE_CLIENT_ID/SECRET, JWT_SECRET, YOUTUBE_API_KEY, EMERGENT_LLM_KEY
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# 2. Frontend
cd ../frontend
yarn install
cp .env.example .env       # set REACT_APP_BACKEND_URL=http://localhost:8001
yarn start                 # http://localhost:3000
```

> 💡 In the Emergent preview environment both services are supervisor-managed — `sudo supervisorctl restart backend|frontend` after `.env` changes.

---

## Environment variables

### `backend/.env`
| Variable               | Purpose                                                  |
| ---------------------- | -------------------------------------------------------- |
| `MONGO_URL`            | MongoDB connection string                                |
| `DB_NAME`              | Mongo database name                                      |
| `JWT_SECRET`           | HMAC secret for session JWTs                             |
| `GOOGLE_CLIENT_ID`     | OAuth client for **Drive** (separate from identity)      |
| `GOOGLE_CLIENT_SECRET` | OAuth secret for Drive                                   |
| `GOOGLE_REDIRECT_URI`  | `https://<host>/api/drive/callback`                      |
| `YOUTUBE_API_KEY`      | YouTube Data API v3 key                                  |
| `EMERGENT_LLM_KEY`     | Universal key for Gemini/OpenAI/Anthropic (OCR phase)    |

### `frontend/.env`
| Variable               | Purpose                                                  |
| ---------------------- | -------------------------------------------------------- |
| `REACT_APP_BACKEND_URL`| Public URL of the FastAPI backend (proxied at `/api/*`)  |

---

## Testing strategy

- **Backend:** `pytest` suite at `backend/tests/test_gate_os_backend.py` — covers auth flow, attempts logging, Drive metadata, and admin role enforcement.
- **Frontend:** smoke + flow tests via the screenshot/automation tooling.
- **Regression:** every iteration writes a structured report to `test_reports/iteration_<n>.json` so we have an auditable trail of what passed and what didn’t.

Run backend tests:
```bash
cd backend
pytest -v
```

---

## Roadmap

Tracked in `memory/PRD.md`. The short version:

### 🔴 P0 — In flight
- **PDF Import + OCR Pipeline** (the moonshot feature)
  - Upload PDF (PYQ booklet, hand-written notes, textbook chapter)
  - **Gemini Nano Banana** via Emergent LLM key → OCR + structural extraction
  - Auto-classify question type (MCQ/MSQ/NAT) and detect options, answer, solution
  - Map to subject/topic via syllabus-aware prompting
  - **Duplicate detection** against existing bank (text-hash + semantic similarity)
  - **Review Queue** in Admin → human approves/edits before commit

### 🟡 P1 — Next
- **Pagination** on Question Bank and PYQs (currently full lists)
- **Edit Questions/PYQs** in Admin (create exists; update is the gap)
- **Bulk CSV upload** for Questions and PYQs (admin productivity)
- **Global Search** — sidebar command palette across subjects, topics, questions, playlists, resources
- **KaTeX math rendering** for question text and solutions (`$...$` and `\(...\)`)

### 🟢 P2 — Later
- **Spaced-repetition Mistake Lab** — surface mistakes via SM-2-style scheduling instead of FIFO
- **Mock test mode** — timed, mixed-subject, with paper-style report card
- **Sharing** — publish a topic’s curated question list as a public read-only page
- **Mobile-first PWA polish** — offline PDF reading, install prompt
- **Refactor** `server.py` → split into `routes/auth.py`, `routes/resources.py`, `routes/playlists.py`, `routes/admin.py` once it crosses ~2k LOC

### 💭 Exploratory
- AI study partner — quiz me on a topic, explain my mistake, generate similar questions
- Notion / Obsidian import for notes
- Discord bot for daily PYQ drops

---

## Engineering notes & deliberate decisions

These are the choices a casual reader would call "weird" and a careful reader would call "correct".

1. **No combined subject completion %.** Solved/Remaining/Accuracy are per-topic only. Aggregating across topics produces a meaningless number that nudges the user toward grinding easy topics. We refuse to ship that metric.

2. **PYQs are a separate collection from `questions`.** They look alike, but conflating them destroys the single most important signal a GATE aspirant has: *"How am I doing on real exam questions vs. practice?"*

3. **Custom canvas PDF viewer instead of Google’s iframe.** Brave and Chrome (with strict tracking protection) block third-party cookies on `drive.google.com` iframes, which silently breaks the embedded viewer. We render PDFs ourselves with `pdfjs-dist` on a `<canvas>`. Bytes are streamed through the backend (`/api/resources/{id}/stream`) using the user’s Drive refresh token — never touching the browser’s third-party cookie jar.

4. **PDF viewer modal uses a React Portal.** Without this, the sidebar overlay z-index war makes the toolbar disappear behind the navigation. The Portal escapes the parent stacking context cleanly.

5. **In-session blob cache for PDFs.** Re-opening the same PDF in the same session would otherwise re-stream the file. We cache the `Blob` URL in a `useRef` map keyed by resource id.

6. **`drive.file` scope, never `drive.readonly` or `drive`.** We only want files we created. The principle of least privilege is also the principle of *"the user trusts you when they shouldn’t have to"*.

7. **Two separate Google OAuth surfaces.** Emergent-managed Google Auth handles *identity*. A dedicated OAuth client handles *Drive storage*. Coupling them means a user who revokes Drive access also loses login — that’s a footgun we refuse to ship.

8. **`is None` checks are intentional.** The static analyzer keeps flagging `dt.tzinfo is None` as an "anti-pattern". It isn’t — that’s PEP-8 canonical. Leave it.

9. **`server.py` is currently monolithic on purpose.** It’s ~1.4k LOC. Premature splitting into routers before the OCR feature lands would create churn. The refactor is scheduled — once the file crosses ~2k LOC or a route file becomes a merge-conflict magnet, we split.

10. **Multi-tenant from line 1.** Every Mongo query carries `user_id`. There is no "tenant later" migration debt waiting in this codebase.

---

## Contributing

This is an active solo project, but PRs are welcome. Conventions:

- **Frontend:** functional components, named exports for components, default exports for pages, Tailwind utility-first, `data-testid` on every interactive element.
- **Backend:** Pydantic v2 schemas at module top, route handlers thin, business logic in helpers; UTC timestamps everywhere (`datetime.now(timezone.utc)`).
- **Commits:** conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`).
- **PRs:** must include or update a `pytest` test if backend logic changes; must include a screenshot if UI changes.

---

## License

MIT — do what you want, just don’t blame me when you actually crack GATE.

---

<p align="center">
  Built with caffeine, spite for bad EdTech, and a deep belief that <br/>
  <strong>your study tools should serve you, not the other way around.</strong>
</p>
