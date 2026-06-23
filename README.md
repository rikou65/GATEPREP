# GATE Study OS

> A high-performance, multi-tenant **Study Operating System** purpose-built for GATE Computer Science (CSE) preparation — Question Banks, PYQs, Mistake Lab, YouTube playlist tracking, and a personal Google-Drive backed resource library, all wired to the official GATE CSE syllabus.

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

Most GATE prep platforms are content silos — they sell you their PDFs, their videos, their question banks. **GATE Study OS** flips that model on its head: it’s an *operating system* you bring your own content to.

- **Your PYQs and questions** live in *your* topic taxonomy.
- **Your resources** (notes, books, cheat sheets) live in *your* Google Drive — we never hold them.
- **Your videos** are real YouTube playlists you already follow; we just track progress.
- **Your mistakes** are first-class artifacts you can revisit until they aren’t mistakes anymore.

The goal: a single, calm dashboard that tells you **what to study next** based on signal, not vibes.

---

## Product principles

1. **No vanity metrics.** We deliberately do **not** show a combined "subject completion %" — it’s a lie that aggregates incomparable things. Topics expose only what is measurable: *Solved, Remaining, Accuracy*.
2. **Accuracy uses latest signal only.** Accuracy is derived ONLY from the latest attempt per question. History is preserved, but current proficiency is what matters. Re-solving a mistake fully overwrites the previous failure signal.
3. **Solutions are inline, never modal.** Reading a solution is part of solving — it shouldn’t take you out of context.
4. **Playlists belong to subjects, not topics.** A real YouTube playlist crosses topic boundaries; forcing the user to lie about that produces bad data.
5. **The user owns the bytes.** Resources are pushed to the user’s own Drive under `GATEPREP/{Type}/{Subject}/`. Disconnect anytime; your files keep working.
6. **No Admin Gatekeeping.** Every user is the super-user of their own data. The legacy admin role is retired; CRUD is available to everyone for their own personal bank.

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
                   │          ├──► Google Identity (Login)
                   │          ├──► Google Drive API (per-user OAuth)
                   │          ├──► YouTube Data API
                   │          └──► Gemini API (Phase 5 - Upcoming)
                   │
            ┌──────▼──────┐
            │   MongoDB   │
            │ (multi-tenant
            │  by user_id)│
            └─────────────┘
```

---

## Tech stack

**Frontend**
- React 19, react-router-dom 7, Tailwind CSS 3.4, Shadcn UI
- `pdfjs-dist` (custom canvas-based renderer)
- `axios` with interceptors for JWT/Cookie management

**Backend**
- FastAPI 0.136, Motor (Async MongoDB), Pydantic v2
- `httpx` for manual OAuth token exchange (no PKCE dependency)
- `StreamingResponse` for memory-efficient resource proxying

**Database**
- MongoDB (Indexing on `user_id` for multi-tenant isolation)
- Aggregation Pipelines for all high-volume analytics

---

## Repository layout

```
.
├── backend/
│   ├── routes/              # Modularized API endpoints
│   ├── tests/               # pytest suite
│   ├── config.py            # Pydantic Settings management
│   ├── server.py            # FastAPI entry point
│   └── shared.py            # Shared DB and Auth helpers
│
├── frontend/
│   ├── src/
│   │   ├── context/         # AuthProvider & State
│   │   ├── components/      # UI components (Viewer, Form, etc.)
│   │   ├── lib/             # API client (Axios)
│   │   └── pages/           # Screen definitions
│   └── public/
│
├── memory/
│   └── PRD.md               # Product Requirements
│
└── README.md
```

---

## Data model

| Collection          | Key fields                                                                                           | Notes                                                   |
| ------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `users`             | `user_id, email, name, picture`                                                                      | Identity via Google OAuth                               |
| `subjects`          | `id, name, order`                                                                                    | 12 official GATE subjects                               |
| `questions`         | `question_id, subject_id, topic_id, type, options, answer, solution`                                 | Practice collection                                     |
| `pyqs`              | same shape as questions + `year`                                                                     | PYQ-specific collection                                 |
| `question_attempts` | `user_id, question_id, is_correct, attempted_at`                                                     | Solving history                                         |
| `resources`         | `user_id, subject_id, title, drive_file_id`                                                          | Metadata for Drive files                                |
| `mistakes`          | `user_id, question_id, mistake_type, note`                                                           | Capture of failures                                     |

---

## API surface

All routes under `/api`. Multi-tenant by `user_id`.

- `POST /api/auth/session` — Exchange Google code for session
- `POST /api/auth/dev-login` — Development bypass (Demo Student)
- `GET  /api/analytics/subject/{id}` — DB-level aggregate stats
- `GET  /api/questions` — Paginated questions with joined attempts
- `GET  /api/resources/{id}/stream` — Chunked Drive proxy stream
- `POST /api/playlists/import` — YouTube Data API ingestion

---

## Local development

### Prerequisites
- Python 3.12+ (Standard Windows distribution)
- Node.js 20+, npm
- MongoDB Atlas cluster

### Quick start

```bash
# 1. Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python seed.py # Populate syllabus
uvicorn server:app --reload

# 2. Frontend
cd ../frontend
npm install --legacy-peer-deps
npm start
```

---

## Environment variables

### `backend/.env`
- `MONGO_URL`: MongoDB connection string
- `JWT_SECRET`: Random string for signing sessions
- `GOOGLE_DRIVE_CLIENT_ID`: Google OAuth client
- `GOOGLE_LOGIN_REDIRECT_URI`: `http://localhost:3000/auth/callback`
- `GOOGLE_DRIVE_REDIRECT_URI`: `http://localhost:8000/api/drive/callback`

---

## Testing strategy

- **Backend:** `pytest` suite in `backend/tests/`. Run with `pytest -v`.
- **Manual Logic:** `self_test_logic.py` for verifying aggregation pipelines.
- **Tokens:** `create_test_tokens.py` for injecting sessions into local DB.

---

## Roadmap

### 🔴 P0 — OCR & PDF Ingestion (Active)
- Gemini-powered extraction of **Questions** and **Key Concepts** from GO-PDFs.
- Staging and Review queues for bulk verification.

### 🟡 P1 — Next
- Pagination on Question Bank/PYQs.
- System-wide **LaTeX rendering** via KaTeX.
- Global Search (Cmd+K).

### 🟢 P2 — Later
- **SM-2 Algorithm** for Spaced Repetition in Mistake Lab.
- Mock Test Mode with timed GATE-style simulations.

---

## Engineering notes & deliberate decisions

1. **DB-Level Aggregation:** We use MongoDB `$lookup` and `$group` for all analytics. This ensures the app stays "instant" even with 5,000+ questions.
2. **Manual OAuth:** We bypass standard libraries for token exchange to avoid PKCE/Verifier conflicts between frontend and backend.
3. **Canvas PDF Engine:** Custom rendering via `pdfjs-dist` ensures the reader works in privacy-hardened browsers.
4. **Admin Role Retired:** To fulfill the "Personal Study OS" vision, every user has full authority over their own data.

---

## License

MIT License. Built for aspirants who believe **study tools should serve you, not silo you.**
