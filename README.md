# GATEPREP

> A GATE CSE preparation website that helps users keep questions, PYQs, playlists, notes, PDFs, and other study resources in one place, organized around the official GATE CSE syllabus.

---

## Table of Contents

- [Overview](#overview)
- [What GATEPREP Helps With](#what-gateprep-helps-with)
- [Feature Tour](#feature-tour)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Layout](#repository-layout)
- [Key Data Model Notes](#key-data-model-notes)
- [API Surface](#api-surface)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Documentation Map](#documentation-map)

---

## Overview

GATEPREP is a website for GATE CSE preparation that brings study material into one
place. The user can manage questions, PYQs, playlists, notes, PDFs, and resources
inside a syllabus-aligned workspace instead of spreading them across multiple tools.

The product currently includes:

- private Question Bank and PYQ practice
- attempt tracking and analytics
- Mistake Lab
- YouTube playlist import and progress tracking
- Google Drive-backed resource storage
- OCR ingestion and staging approval flow for PDFs

---

## What GATEPREP Helps With

GATEPREP is built to help users:

- keep study resources in one place
- organize content by the official GATE CSE syllabus
- practice from both question banks and PYQs
- track progress from actual study activity
- keep notes and resources close to the material being studied
- import useful material from PDFs and playlists into the same workflow

---

## Feature Tour

### Dashboard
- overview stats
- subject-level progress
- analytics entry point

### Subjects and Practice
- official GATE CSE subject and topic taxonomy
- Question Bank
- PYQs
- attempt history and accuracy

### Mistake Lab
- user-owned mistake tracking
- review-oriented study workflow

### Playlists
- YouTube playlist import
- inline playback
- progress tracking
- video notes

### Resources
- Drive connection
- resource upload and sync
- PDF viewing
- resource notes

### OCR and Staging
- PDF ingestion
- OCR import jobs
- staging queue
- approve/discard workflow into live content

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the detailed domain map and current technical shape.

High-level stack:

```text
React + Vite frontend
        |
        v
FastAPI backend (/api/*)
        |
        v
MongoDB + Google Drive + Google OAuth + YouTube OAuth + Mistral OCR
```

Current local reality:

- frontend runs on `127.0.0.1:3000`
- backend runs on `127.0.0.1:8001`
- frontend backend env is `VITE_BACKEND_URL`
- OCR/staging routes are under `/api/data/*`

---

## Tech Stack

### Frontend
- React
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack React Query

### Backend
- FastAPI (layered architecture: endpoints → services → repositories)
- Motor + MongoDB
- Pydantic

### Integrations
- Google OAuth (login + Drive + YouTube)
- Supabase Auth (dual-auth compatible)
- Google Drive API
- YouTube API / IFrame player
- Mistral OCR

---

## Repository Layout

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   ├── responses.py
│   │   │   └── endpoints/       (auth, subjects, practice, analytics,
│   │   │                         playlists, resources, youtube, staging)
│   │   ├── core/                (config, db, time, ids, security, constants, logging)
│   │   ├── schemas/             (canonical Pydantic models)
│   │   ├── services/            (business logic)
│   │   ├── repositories/        (MongoDB access)
│   │   ├── integrations/        (google_oauth, supabase_auth, google_drive, google_youtube)
│   │   ├── bootstrap/           (seed data and migration startup)
│   │   └── tasks/               (background workers placeholder)
│   ├── tests/
│   ├── scripts/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                 (typed client, query keys, endpoint modules)
│   │   ├── components/
│   │   ├── context/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── playlists/
│   │   │   ├── resources/
│   │   │   ├── settings/
│   │   │   ├── staging/
│   │   │   └── subjects/
│   │   ├── lib/
│   │   ├── types/
│   │   └── pages/
├── ARCHITECTURE.md
├── AUTH_STRATEGY.md
├── CONTRIBUTING.md
├── IMPLEMENTATION_ROADMAP.md
├── OCR_PIPELINE.md
└── README.md
```

---

## Key Data Model Notes

Important user-owned collections include:

- `questions`
- `pyqs`
- `question_attempts`
- `mistakes`
- `resources`
- `playlists`
- `videos`
- `video_progress`
- `video_notes`
- `staging_questions`
- `import_jobs`

Important rules:

- user-owned collections must carry `user_id`
- playlist/video operations must verify ownership
- OCR/staging data must remain tenant-safe

---

## API Surface

Canonical backend prefix: `/api`

Examples:

### Auth
- `POST /api/auth/session`
- `POST /api/auth/dev-login`
- `GET /api/auth/me`

### Practice
- `GET /api/questions`
- `POST /api/questions`
- `GET /api/pyqs`

### Analytics
- `GET /api/dashboard`
- `GET /api/analytics/subject/{subject_id}`
- `GET /api/analytics/topic/{topic_id}`

### Playlists
- `POST /api/playlists/import`
- `GET /api/playlists`
- `GET /api/playlists/{playlist_id}`
- `POST /api/videos/{video_id}/progress`
- `GET /api/videos/{video_id}/notes`
- `POST /api/videos/{video_id}/notes`

### Resources
- `GET /api/resources`
- `POST /api/resources/upload`
- `GET /api/resources/{resource_id}/stream`

### OCR / Staging
- `POST /api/data/import/pdf`
- `GET /api/data/import/jobs`
- `GET /api/data/staging`

---

## Local Development

### Backend

```powershell
cd backend
& ../venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Frontend

```powershell
cd frontend
node_modules/.bin/vite.cmd --host 127.0.0.1 --port 3000 --strictPort
```

### Auth and OAuth notes

- Supabase Auth is the primary login path for Google and email/password.
- MongoDB remains the application database; Supabase is auth-only.
- Legacy Google login can remain temporarily as a fallback until Supabase is fully verified.
- Drive and YouTube use their own Google OAuth flows and do not reuse Supabase provider tokens.
- Local Google Drive and YouTube OAuth may show tester/verification limits until the Google Cloud OAuth consent screen is published or the account is added as a tester.

---

## Environment Variables

This README only lists the commonly used local variables. For exact templates, use:

- [frontend/.env.example](./frontend/.env.example)
- [backend/.env.example](./backend/.env.example)

### Frontend common variables

Example `frontend/.env`:

```env
VITE_BACKEND_URL=http://127.0.0.1:8001
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_GOOGLE_CLIENT_ID=  (deprecated — login URL now built server-side via /auth/google-url)
VITE_GOOGLE_LOGIN_REDIRECT_URI=http://127.0.0.1:3000/auth/callback  (deprecated — login redirect managed server-side)
```

### Backend common variables

Typical `backend/.env` values:

- `MONGO_URL`
- `DB_NAME`
- `JWT_SECRET`
- `GOOGLE_DRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET`
- `GOOGLE_LOGIN_REDIRECT_URI`
- `GOOGLE_DRIVE_REDIRECT_URI`
- `GOOGLE_YOUTUBE_REDIRECT_URI`
- `SUPABASE_URL`
- `SUPABASE_JWT_SECRET`
- `FRONTEND_URL`
- `YOUTUBE_API_KEY`
- `MISTRAL_API_KEY`
- `ENVIRONMENT`

For descriptions and current examples, check the `.env.example` files directly.

---

## Documentation Map

- [ARCHITECTURE.md](./ARCHITECTURE.md)  
  Current domains, technical shape, and pain points.

- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)  
  Active roadmap and execution order.

- [OCR_PIPELINE.md](./OCR_PIPELINE.md)  
  OCR ingestion and staging behavior.

- [CONTRIBUTING.md](./CONTRIBUTING.md)  
  Contribution rules, coding conventions, and testing expectations.
