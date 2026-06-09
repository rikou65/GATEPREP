# GATE Study OS — Implementation Plan & Feature Backlog

> A pragmatic, sequenced engineering plan for everything left to build, plus a curated list of features worth considering. Treat this as a working document — re-prioritise at the end of every shipped phase.

**Last updated:** Feb 2026
**Maintainer:** @you
**Status legend:** 🔴 P0 (next) · 🟡 P1 (queued) · 🟢 P2 (later) · 💭 Idea (unvalidated)

---

## Table of Contents

1. [How to read this document](#how-to-read-this-document)
2. [Current state recap](#current-state-recap)
3. [Phase 5 — PDF Import + OCR Pipeline 🔴](#phase-5--pdf-import--ocr-pipeline-)
4. [Phase 6 — Pagination, Editing & Bulk Tools 🟡](#phase-6--pagination-editing--bulk-tools-)
5. [Phase 7 — Global Search & Math Rendering 🟡](#phase-7--global-search--math-rendering-)
6. [Phase 8 — Spaced Repetition & Mock Tests 🟢](#phase-8--spaced-repetition--mock-tests-)
7. [Phase 9 — Backend Refactor 🟢](#phase-9--backend-refactor-)
8. [New feature suggestions 💭](#new-feature-suggestions-)
9. [Cross-cutting hardening](#cross-cutting-hardening)
10. [Definition of Done](#definition-of-done)

---

## How to read this document

Each phase follows the same template:

- **Goal** — one sentence, user-facing.
- **Why now** — what unlocks if we ship this.
- **Scope (in / out)** — strict boundary to avoid scope creep.
- **User stories** — what the user can do at the end.
- **Technical breakdown** — backend, frontend, DB, integrations.
- **Risks & mitigations** — what will probably go wrong.
- **Acceptance criteria** — how we know it's done.
- **Estimated effort** — engineer-days, optimistic.

Ship one phase end-to-end before starting the next. No half-finished features in `main`.

---

## Current state recap

| Module                  | Status      | Notes                                                              |
| ----------------------- | ----------- | ------------------------------------------------------------------ |
| Auth (Emergent Google)  | ✅ Done     | JWT sessions, multi-tenant                                         |
| 12 GATE CSE subjects    | ✅ Done     | Aligned to official syllabus                                       |
| Question Bank (MCQ/MSQ/NAT) | ✅ Done | Inline solutions, attempt logging                                  |
| PYQs (separate)         | ✅ Done     | Year filter, independent accuracy                                  |
| Mistake Lab             | ✅ Done     | Derived view from attempts                                         |
| Playlists + tracking    | ✅ Done     | YouTube IFrame + auto-progress                                     |
| Drive Resources         | ✅ Done     | `drive.file` scope, custom PDF canvas viewer                       |
| Admin (basic CRUD)      | ✅ Done     | Create only — edit/delete partial                                  |
| **OCR Pipeline**        | 🔴 Next     | Phase 5                                                            |
| Pagination              | 🟡 Backlog  | Phase 6                                                            |
| Question/PYQ edit       | 🟡 Backlog  | Phase 6                                                            |
| CSV bulk upload         | 🟡 Backlog  | Phase 6                                                            |
| Global Search           | 🟡 Backlog  | Phase 7                                                            |
| KaTeX rendering         | 🟡 Backlog  | Phase 7                                                            |

---

## Phase 5 — PDF Import + OCR Pipeline 🔴

### Goal
Let admins upload a PDF (PYQ booklet, textbook chapter, hand-written notes) and have the system extract structured questions, classify them, map them to topics, detect duplicates, and queue them for human review before they enter the question bank.

### Why now
This is the **moonshot**. Every other GATE platform ships pre-curated questions. We let the user grow their bank from any source. It also turns the PYQ archive (40+ years of papers) into a 1-evening import job instead of a 1-year manual data-entry chore.

### Scope

**In:**
- PDF upload through Admin → backend pipeline → Review Queue UI.
- Gemini Nano Banana (via Emergent LLM key) for OCR + structural extraction.
- Auto-classify type (MCQ / MSQ / NAT) and detect options, correct answer, solution.
- Subject/Topic suggestion using a syllabus-aware prompt.
- Duplicate detection (text-hash + cosine similarity on embeddings).
- Review Queue with approve / edit / reject / merge-with-duplicate actions.
- Bulk approve.

**Out (intentionally):**
- Live OCR feedback (we'll show "processing" status; user comes back to it).
- Image extraction from questions (Phase 5.5 if user demands it).
- Math rendering inside extracted questions (handled in Phase 7 via KaTeX).
- Non-PDF input (images, DOCX) — Phase 5.5.

### User stories
1. As an admin, I upload `GATE_2023_CSE.pdf` and within ~2 minutes see N extracted questions in a Review Queue.
2. As an admin, I see each extracted question with: question text, options, suggested answer, suggested subject + topic, confidence score, and a "likely duplicate of X" warning if applicable.
3. As an admin, I can edit any field inline, then click **Approve** to commit to `pyqs` (or `questions`).
4. As an admin, I can bulk-approve all questions above a confidence threshold.

### Technical breakdown

#### Backend
- **New collections:**
  - `pdf_imports` — `{id, user_id, filename, drive_file_id, status, total_pages, processed_pages, total_questions_extracted, created_at, completed_at, error}`
  - `extracted_questions` — `{id, import_id, page_number, raw_text, question_text, type, options, correct_answer, solution, subject_id_suggested, topic_id_suggested, confidence, duplicate_of, status: pending|approved|rejected|merged, reviewed_by, reviewed_at}`
- **New endpoints:**
  - `POST /api/admin/imports/pdf` *(multipart)* → uploads PDF, creates `pdf_imports` row, kicks off async job, returns `import_id`.
  - `GET  /api/admin/imports/{id}` → progress + summary.
  - `GET  /api/admin/imports/{id}/extracted` → paginated extracted questions.
  - `PUT  /api/admin/imports/extracted/{id}` → edit a single extracted question.
  - `POST /api/admin/imports/extracted/{id}/approve` → commit to `questions` or `pyqs`.
  - `POST /api/admin/imports/extracted/{id}/reject`
  - `POST /api/admin/imports/extracted/{id}/merge` → `{target_id}` — drop this one, mark canonical.
  - `POST /api/admin/imports/{id}/bulk-approve` → `{min_confidence}`.
- **Async pipeline (FastAPI BackgroundTasks for v1, Celery/RQ later):**
  1. PDF → page splitter (`pdfplumber` or `PyMuPDF`).
  2. Each page → image (300 DPI) — Gemini Nano Banana handles vision directly, so we send images, not extracted text. This gives us better fidelity on math, tables, and hand-written content.
  3. Page image → Gemini prompt: "Extract every question on this page as JSON matching this schema…". Use **structured output** (`response_mime_type: application/json`).
  4. Per extracted question → second Gemini call with the syllabus-aware classifier prompt: "Given GATE CSE syllabus [...], assign subject_id and topic_id."
  5. Compute SHA-256 of normalised question text; check against existing `questions`/`pyqs` for **exact duplicates** → if hit, mark `duplicate_of`.
  6. Compute embedding (`text-embedding-3-small` or Gemini embeddings) → cosine similarity ≥ 0.92 → mark as **likely duplicate** with a lower-confidence flag.
  7. Update `pdf_imports.processed_pages` after each page so the UI can show progress.
- **Prompt engineering** lives in `backend/prompts/`:
  - `ocr_extract.md`
  - `topic_classify.md` (contains the full syllabus tree, regenerated from DB at startup)
- **Concurrency:** rate-limit Gemini calls to N/sec (configurable env var), exponential backoff on 429.

#### Frontend
- **New page:** `pages/AdminImports.jsx` — list of imports with status pills, click to drill in.
- **New page:** `pages/AdminImportReview.jsx` — table of `extracted_questions`:
  - Columns: page, question preview, type, suggested topic, confidence, duplicate-of, status, actions.
  - Filters: status, type, confidence range, "has duplicate".
  - Row click → inline expand with full editor (`QuestionEditor.jsx` — reusable).
  - Sticky toolbar: "Approve selected", "Bulk approve ≥ 0.85 confidence", "Reject selected".
- **Reusable component:** `QuestionEditor.jsx` — used here, in Admin CRUD (Phase 6), and anywhere else we edit a question.

#### Risks & mitigations
| Risk                                          | Mitigation                                                                                  |
| --------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Gemini hallucinates options / answers         | Confidence score + review queue is mandatory; nothing auto-commits.                          |
| Large PDFs blow up memory                     | Process page-by-page; stream the file from disk, never load whole PDF.                       |
| Cost runaway on Emergent LLM key              | Per-user daily quota; surface "estimated cost: $X" before kicking off.                      |
| Duplicate detection misses paraphrases        | Two-layer: exact hash + embedding cosine. Tune threshold after first 500 real imports.       |
| Math-heavy questions extract poorly           | Send images to Gemini (vision) not pre-extracted text; pair with KaTeX rendering (Phase 7). |

#### Acceptance criteria
- [ ] Upload a real GATE PYQ PDF (`GATE_2023_CSE.pdf`) and end up with ≥ 80% of questions extracted correctly.
- [ ] Confidence score is calibrated: ≥ 0.85 questions are correct ≥ 90% of the time on a 50-question sample.
- [ ] Duplicate detection catches 100% of exact-text duplicates and ≥ 80% of paraphrases.
- [ ] Admin can go from "PDF on disk" to "100 PYQs in bank" in ≤ 10 minutes of human time.
- [ ] No Gemini call is made without an explicit user action (no auto-retry storms).

#### Estimated effort
**8–12 engineer-days.** This is the biggest single feature. Budget accordingly.

---

## Phase 6 — Pagination, Editing & Bulk Tools 🟡

### Goal
Make the admin/teacher workflow not-painful at scale. Currently the question bank UX assumes ≤ 200 items.

### Scope

**In:**
1. **Server-side pagination** on `GET /api/questions` and `GET /api/pyqs`:
   - Query params: `?page=1&page_size=25&sort=created_at_desc`.
   - Response: `{items, total, page, page_size, total_pages}`.
   - Frontend: shadcn `Pagination` component, persist page in URL query.
2. **Edit Questions/PYQs in Admin**:
   - `PUT /api/admin/questions/{id}` and `PUT /api/admin/pyqs/{id}`.
   - Reuse `QuestionEditor.jsx` from Phase 5.
   - Optimistic UI update, rollback on error.
3. **Bulk CSV upload**:
   - Endpoint: `POST /api/admin/questions/bulk` *(multipart CSV)*.
   - Validate per-row → return `{accepted: N, rejected: [{row, error}, ...]}`.
   - Template CSV downloadable from the Admin page.
   - Columns: `subject_name, topic_name, type, question_text, option_a, option_b, option_c, option_d, correct_answer, solution, difficulty, year` (year only for PYQs).

**Out:** Excel/`.xlsx` import (CSV only for v1).

### Technical notes
- Add Mongo indexes: `{subject_id: 1, topic_id: 1, created_at: -1}` on `questions` and `pyqs`.
- For CSV: stream-parse using `csv` stdlib — never load the whole file.
- Subject/Topic lookup by name with auto-create-or-fail policy (config flag).

### Acceptance criteria
- [ ] Question Bank loads in ≤ 200ms with 10k questions in the bank.
- [ ] Edit flow works without page reload.
- [ ] CSV with 500 rows imports in ≤ 30s and surfaces per-row errors clearly.

### Estimated effort
**3–4 engineer-days.**

---

## Phase 7 — Global Search & Math Rendering 🟡

### Goal
1. A `Cmd+K` palette that searches across everything.
2. Math actually renders like math, not `$\sum_{i=1}^n$`.

### Scope

**In:**
1. **Global Search**:
   - Frontend: `cmdk` (already in dependencies) → keyboard shortcut `Cmd/Ctrl+K` opens overlay.
   - Backend: single endpoint `GET /api/search?q=...&types=questions,pyqs,playlists,resources,topics`.
   - Strategy: MongoDB **Atlas Search** if available, otherwise per-collection `$text` indexes.
   - Indexes:
     - `questions`: `{question_text: "text", solution: "text"}`
     - `pyqs`: same + `year`
     - `playlists`: `{title: "text"}`
     - `resources`: `{title: "text"}`
     - `topics`/`subjects`: `{name: "text"}`
   - Response: grouped by type, each group `{type, items: [{id, title, snippet, url}]}`.
   - Frontend renders grouped sections, arrow-key navigation, Enter to navigate.
2. **KaTeX math rendering**:
   - Add `katex` + `react-katex` to frontend.
   - New component `MathText.jsx` that renders a string containing `$...$` (inline) and `$$...$$` (block) using `react-katex`.
   - Use it in:
     - `QuestionViewer.jsx` (question text + options + solution)
     - `MistakeLab.jsx`
     - Admin extract/edit views
   - Add a "Math preview" panel in `QuestionEditor.jsx` so editors see what they're typing.

**Out:**
- Fuzzy/semantic search (Phase 8 candidate — embeddings on question text).
- MathML import (KaTeX-supported LaTeX syntax only).

### Acceptance criteria
- [ ] Cmd+K opens, types-to-filter under 50ms perceived latency.
- [ ] LaTeX in a question like `$\sum_{i=1}^n i = \frac{n(n+1)}{2}$` renders as math.
- [ ] No KaTeX errors crash the page (wrap in `ErrorBoundary` with raw-text fallback).

### Estimated effort
**3–4 engineer-days.**

---

## Phase 8 — Spaced Repetition & Mock Tests 🟢

### Goal
Two features that turn "I have a question bank" into "I have a learning system".

### Scope

#### 8A. Spaced-Repetition Mistake Lab
- Replace FIFO mistake list with an **SM-2** scheduler.
- New collection: `review_schedule` — `{user_id, question_id|pyq_id, ease, interval, repetitions, next_review_at}`.
- After every mistake re-attempt:
  - If correct → grade based on time taken (`easy / good / hard`) → update ease + interval.
  - If wrong → reset interval, ease −0.2.
- Mistake Lab home becomes a **"Due today: N"** card. Click → enter review session.
- New endpoints:
  - `GET /api/reviews/due`
  - `POST /api/reviews/{schedule_id}/grade` → `{grade: easy|good|hard|wrong}`

#### 8B. Mock Test Mode
- Configurable mock: subject mix, total questions, total time.
- "GATE-style" preset: 65 questions / 180 minutes / mixed MCQ/MSQ/NAT with negative marking.
- During mock: locked timer, navigator pane, mark-for-review, no solutions visible.
- After submit: **Report card** — section-wise accuracy, time per question, weakest topics, top 5 mistakes, downloadable PDF (use `@react-pdf/renderer`).
- New collections:
  - `mock_tests` — config + question_ids
  - `mock_attempts` — `{mock_id, user_id, started_at, submitted_at, answers, score, breakdown}`

### Risks
- Mock test state must survive a tab refresh. Persist `mock_attempts` every 30s.
- Negative marking arithmetic is famously easy to get wrong — write unit tests **first**.

### Estimated effort
**6–8 engineer-days** (SR: 3, Mock: 5).

---

## Phase 9 — Backend Refactor 🟢

### Goal
Split `server.py` (~1.4k LOC, growing fast) into a proper modular FastAPI app before it becomes a merge-conflict nightmare.

### Trigger
Begin **only when** any of these is true:
- `server.py` crosses 2000 LOC.
- Two devs are working in parallel and hitting conflicts.
- Test runtime exceeds 30s due to monolithic imports.

### Target structure
```
backend/
├── server.py                     # 50-line app factory + router includes
├── core/
│   ├── config.py                 # Settings via pydantic-settings
│   ├── db.py                     # Mongo client + collection helpers
│   ├── security.py               # JWT, password, role checks
│   └── deps.py                   # FastAPI dependencies
├── routes/
│   ├── auth.py
│   ├── subjects.py
│   ├── questions.py
│   ├── pyqs.py
│   ├── playlists.py
│   ├── resources.py             # Drive routes
│   ├── admin.py
│   └── imports.py               # OCR pipeline (Phase 5)
├── services/
│   ├── drive.py                 # All Google Drive logic
│   ├── youtube.py
│   ├── ocr.py                   # Gemini extraction + classification
│   └── search.py                # Phase 7
├── schemas/                      # Pydantic models, one file per entity
└── tests/
```

Refactor in one PR, with the test suite as the safety net. **Do not** mix refactor with new features.

### Estimated effort
**2 engineer-days** if test coverage is solid by then.

---

## New feature suggestions 💭

Curated list of ideas worth validating against real users before building. Ordered by *impact × ease*.

### 1. **AI Study Partner** ★★★★★
Conversational LLM tutor scoped to a specific question/topic. Use cases:
- "Explain why my answer was wrong" — pass user's answer + correct answer + solution to Gemini.
- "Give me a similar question" — generate a fresh question on the same topic.
- "Walk me through this topic" — generate a 5-minute primer.

**Tech:** Gemini via Emergent LLM key. Streaming responses. Conversation context capped at ~10 turns.

### 2. **Streak & Daily Goal** ★★★★☆
The gamification spine.
- Daily goal: configurable (e.g., 10 questions / 1 PYQ / 30 min video).
- Streak counter on dashboard.
- "Don't break the chain" calendar heatmap (like GitHub contributions).
- Push notification / email reminder at user-chosen time.

**Tech:** Cron via APScheduler or a simple `last_active_at` check. Resend for email (already on the integration shortlist).

### 3. **Topic Mastery Score** ★★★★☆
Per-topic, not global. Weighted formula combining:
- Recent accuracy (last 20 attempts)
- Time-to-correct trend (improving?)
- Mistake recurrence (same question wrong twice = penalty)
- Time since last activity (decay)

Surface as a *Topic Heatmap* on the dashboard. Users see at a glance which 3 topics to attack next.

### 4. **Smart "Today's Plan"** ★★★★★
The dashboard's `Continue` card gets smarter:
- 3 due reviews (from Phase 8 SR)
- 5 questions from your weakest topic
- 1 video to watch (next in your highest-progress playlist)
- 1 PYQ from a year you haven't touched in 7 days

One click → start a session. This is the single most valuable feature a daily-use app can have.

### 5. **Cohort / Study Group (read-only sharing)** ★★★☆☆
Invite friends via email → they see your *aggregate* stats (accuracy by subject) but not individual answers.
Optional weekly digest: "Your group's top topic this week was OS · Scheduling."

**Tech:** New `cohorts` collection with `members: [user_id]`. Tight permission checks.

### 6. **Mock Test Marketplace** ★★★☆☆
Admins can publish a mock test (set of question ids + config) as a public link. Other users take it (anonymously or signed-in) and get a report. Builds organic acquisition.

### 7. **Notion / Obsidian / Markdown Notes Import** ★★★☆☆
Upload a `.md` file → parse headings → create a Resource entry with full-text searchable content. Pairs perfectly with the Global Search palette.

### 8. **Voice-First Quick Review** ★★☆☆☆
On mobile, "Hey Study OS, quiz me on OS" → reads question via TTS, listens for answer via STT. Hands-free revision while walking.
**Tech:** OpenAI Whisper (STT) + OpenAI TTS — both available via Emergent LLM key.

### 9. **PYQ Trend Analyzer** ★★★★☆
Auto-analysis: "TOC has appeared in 87% of GATE papers since 2015, with regular expressions being the most common subtopic." Visualised as a heatmap over years × topics. Drives study priority.

**Tech:** Simple aggregation pipeline once PYQs are densely populated (Phase 5 helps here).

### 10. **Distraction-Free Study Mode** ★★★☆☆
Toggle that hides the sidebar, dashboard, and notifications. Just question → solve → next. Configurable session length (Pomodoro: 25/5). At session end, show breakdown.

### 11. **Anki-style Card Export** ★★☆☆☆
Export your mistake lab as an Anki `.apkg` file. For users who already have an Anki habit.

### 12. **Telegram Bot Integration** ★★★☆☆
- `/today` → today's plan in chat
- `/pyq` → daily PYQ delivered to chat
- `/streak` → current streak

Push delivery to where students already live.

### 13. **Calibration Quiz (onboarding)** ★★★★☆
First-time users take a 30-question diagnostic across all 12 subjects → system seeds the Topic Mastery Score → personalises Today's Plan from day 1. Cuts time-to-value from weeks to minutes.

### 14. **Public Profile / Portfolio** ★★☆☆☆
Opt-in `studyos.dev/u/yourname` showing your streak, accuracy, total questions solved, top subjects. Shareable, possibly recruiter-relevant.

### 15. **Differential Difficulty (auto-tune)** ★★★☆☆
Track each question's *actual* difficulty based on aggregate accuracy across users (Item Response Theory). Re-rank "Easy / Medium / Hard" labels with reality. Power feature once user base is non-trivial.

---

## Cross-cutting hardening

Things that aren't features but matter for production:

| Area              | Item                                                                              | Priority |
| ----------------- | --------------------------------------------------------------------------------- | -------- |
| Observability     | Structured logs (JSON), request IDs, basic metrics via Prometheus exporter        | 🟡       |
| Error tracking    | Sentry on frontend + backend                                                      | 🟡       |
| Rate limiting     | Per-user limits on LLM-backed endpoints (OCR, AI study partner)                   | 🔴 with Phase 5 |
| Backup            | Daily Mongo dump → S3-compatible bucket                                           | 🟡       |
| Tests             | Push backend coverage to 70%; add Playwright e2e for top 5 flows                  | 🟡       |
| CI/CD             | GitHub Actions: lint → test → build → preview deploy                              | 🟡       |
| Accessibility     | Audit with axe-core; ensure keyboard nav on Cmd+K, modals, question viewer        | 🟢       |
| Mobile polish     | Responsive audit on Resources, PlaylistDetail, Admin tables                       | 🟡       |
| Security          | CSP headers, rate-limit on auth endpoints, JWT rotation                           | 🟡       |
| GDPR/Data export  | `GET /api/me/export` → ZIP of all user data (attempts, resources metadata, etc.) | 🟢       |

---

## Definition of Done

A feature isn't "done" until:

1. ✅ Backend route exists with Pydantic schema validation.
2. ✅ Frontend page/component uses it with proper loading + error states.
3. ✅ Every interactive element has a `data-testid`.
4. ✅ At least one `pytest` test covers the happy path; one covers an error path.
5. ✅ Frontend smoke-tested via the testing agent OR Playwright script.
6. ✅ `PRD.md` / `CHANGELOG.md` updated.
7. ✅ If new env vars: documented in this file **and** the `.env.example`.
8. ✅ If auth credentials touched: `memory/test_credentials.md` updated.
9. ✅ No new lint warnings.
10. ✅ Manual QA: works in Chrome, Firefox, **and Brave** (the third-party-cookie canary).

---

## Sequencing recommendation (next 6 weeks)

| Week | Focus                                                            |
| ---- | ---------------------------------------------------------------- |
| 1–2  | **Phase 5** — OCR Pipeline (P0)                                  |
| 3    | **Phase 6** — Pagination, edit, CSV bulk                         |
| 4    | **Phase 7** — Global search + KaTeX                              |
| 5    | **Phase 8A** — Spaced-repetition Mistake Lab                     |
| 6    | **Smart Today's Plan** + **Streak** (from Suggestions §2 & §4)   |

Re-evaluate after Week 6 against real-user feedback.

---

<p align="center">
  <em>Plans are worthless. Planning is everything. — Eisenhower</em>
</p>
