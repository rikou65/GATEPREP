# GATE Study OS — PRD

## Original Problem Statement
Build a GATE Preparation Platform "Study Operating System" — personal study OS, NOT coaching/social/leaderboard. Subject → Topic only (official GATE CSE syllabus). Tracks Question Bank, PYQs, Playlists, Notes, Mistakes, Resources separately. Inline solutions, YouTube IFrame playback, dark Notion-like UI.

## Architecture
- Backend: FastAPI + MongoDB (motor), prefix /api
- Frontend: React 19 + react-router + axios + recharts + shadcn/ui (dark theme)
- Auth: Emergent-managed Google OAuth (cookie + Bearer token)
- YouTube import: YouTube Data API v3 (key in backend/.env)

## Implemented (2026-02)
- Auth: /api/auth/session, /auth/me, /auth/logout (cookie + Bearer)
- Syllabus seeded: 10 GATE CSE subjects + ~50 topics
- Question Bank: list/filter (subject/topic/type/difficulty), attempt with grading (MCQ/MSQ/NAT), notes (auto-save), attempt history
- PYQs: parallel system with separate progress/analytics
- Mistake Lab: log/filter/delete with mistake_type
- Playlists: YouTube URL → fetch via YT Data API (title/thumbnail/video list/durations); play inside platform with IFrame API + progress tracking (>=90% completed)
- Resources: metadata + external URL link, by subject/type
- Dashboard: 8 summary cards, per-subject QB vs PYQ overview
- Analytics: subject and topic analytics endpoints, recharts BarCharts
- Admin: add Question/PYQ, list users (first user is auto-admin)
- ~12 sample questions + 6 PYQs seeded

## Strict rules enforced
- No combined subject completion %
- QB and PYQ tracked separately
- Solutions inline (Show/Hide toggle)
- No manual topic statuses — only measurable metrics
- YouTube videos play inside platform

## Deferred (P1)
- Google Drive OAuth + file upload abstraction
- PDF Import + OCR pipeline (Tesseract/Vision)
- Admin Review Queue + duplicate detection
- Global search
- Rate limiting

## Next tasks
- Add KaTeX math rendering in solutions
- Add subject-level analytics page UI consumption (endpoint exists)
