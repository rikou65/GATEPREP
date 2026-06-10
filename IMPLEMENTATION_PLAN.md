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
Ingest the **GateOverflow `GO-PDFs` corpus** (every GATE CSE PYQ since 1987 + topic-wise volumes containing both key concepts and questions) and let admins also upload arbitrary PDFs (textbook chapters, hand-written notes). The pipeline extracts structured **key concepts** and **questions**, classifies them, maps them to subject/topic, detects duplicates, and queues them for human review before they enter the live bank.

### Why now
This is the **moonshot**. It does two things simultaneously:
1. Turns the GO-PDFs (~40 years of curated PYQs + topic-wise key concept material) into a 1-evening import job instead of a 1-year manual data-entry chore.
2. Establishes the OCR pipeline so any future PDF (textbook chapter, scanned notes, coaching booklet) becomes ingestible the same way.

### Source corpus
- **Primary:** https://github.com/GATEOverflow/GO-PDFs releases — comprehensive PDFs published by the GO admins themselves under CC-style attribution norms. Contains:
  - **Year-wise PYQ volumes** (1987 → latest GATE).
  - **Topic-wise volumes** (Engineering Mathematics, Discrete Math, DSA, OS, DBMS, CN, COA, TOC, Compilers, Digital Logic, Algorithms, Aptitude) — these contain **both key concept summaries and questions on the same topic**.
- **Secondary:** any admin-uploaded PDF (custom path through the same pipeline).

### Scope

**In:**
- Download GO-PDFs latest release via GitHub API (one-shot CLI script).
- Admin upload of arbitrary PDFs through the same pipeline.
- Gemini Nano Banana (via Emergent Universal LLM key) for OCR + **dual-mode structural extraction**:
  - **Key concept sections** → `{title, content_markdown, suggested_topic, confidence}`
  - **Questions** → `{question_text, type, options, correct_answer, solution, suggested_subject, suggested_topic, confidence}`
- Per-page content-type classification (concepts only / questions only / mixed).
- Subject/Topic suggestion using a syllabus-aware prompt (12 GATE CSE subjects baked in).
- Duplicate detection:
  - Concepts: text-hash on normalised title + content; later, embedding cosine.
  - Questions: text-hash on question_text + options; embedding cosine ≥ 0.92.
- **Two parallel Review Queues** in Admin:
  - `extracted_concepts` → reviewed → committed to `topic_concepts`.
  - `extracted_questions` → reviewed → committed to `questions` / `pyqs`.
- Bulk approve above a confidence threshold.
- Attribution: every imported item stores `source` (e.g., `"GateOverflow Digital Logic v4"`) and `source_url`.

**Out (intentionally):**
- Image extraction from inside questions (Phase 5.5).
- Live OCR feedback (we show "processing", user returns to the queue later).
- DOCX/image inputs (Phase 5.5).
- Math rendering inside the queue UI (handled in Phase 7 via KaTeX — but the **extracted markdown already contains LaTeX** so Phase 7 unlocks display).

### User stories
1. **As an admin**, I run `python -m backend.scripts.import_go_pdfs` and within ~1–2 hours I see N extracted concepts + M extracted questions in two review queues.
2. **As an admin**, I upload `GATE_2025_CSE.pdf` and within ~2 minutes see its concepts and questions extracted.
3. **As an admin**, each extracted item shows confidence + suggested subject/topic + duplicate warnings + source attribution. I can edit any field inline, then approve.
4. **As an admin**, I can bulk-approve everything above 0.85 confidence.
5. **As a student**, when I open a topic detail page I now see a **"Key Concepts"** section above the QBank/PYQ buttons — short, dense, LaTeX-rendered summaries imported from the GO-PDFs corpus.

### Technical breakdown

#### New data model
**Existing untouched.** Add **one new collection** — `topic_concepts`:
```
concept_id        string (pk)
topic_id          string (fk → topics)
subject_id        string (fk, denormalised)
title             string
content_markdown  string   (LaTeX inside $...$ blocks)
position          int      (display order within topic)
source            string   (e.g., "GateOverflow Digital Logic v4")
source_url        string   (back-link for attribution)
created_at, updated_at
```

Plus two **staging collections** for the pipeline:
- `pdf_imports` — `{id, user_id, filename, drive_file_id|local_path, status, total_pages, processed_pages, total_concepts_extracted, total_questions_extracted, created_at, completed_at, error}`
- `extracted_concepts` — staging row per extracted concept: `{id, import_id, page_number, title, content_markdown, suggested_subject_id, suggested_topic_id, confidence, duplicate_of, source, source_url, status: pending|approved|rejected|merged, reviewed_by, reviewed_at}`
- `extracted_questions` — same shape as before + `source`, `source_url`.

#### New backend endpoints
- `POST /api/admin/imports/pdf` *(multipart)* — kicks off async pipeline, returns `import_id`.
- `GET  /api/admin/imports` — list all imports with status.
- `GET  /api/admin/imports/{id}` — progress + summary.
- `GET  /api/admin/imports/{id}/extracted-concepts` — paginated.
- `GET  /api/admin/imports/{id}/extracted-questions` — paginated.
- `PUT  /api/admin/imports/extracted-concepts/{id}` — edit.
- `PUT  /api/admin/imports/extracted-questions/{id}` — edit.
- `POST /api/admin/imports/extracted-concepts/{id}/approve` → commit to `topic_concepts`.
- `POST /api/admin/imports/extracted-questions/{id}/approve` → commit to `questions` or `pyqs`.
- `POST /api/admin/imports/extracted-{concepts|questions}/{id}/reject`.
- `POST /api/admin/imports/extracted-{concepts|questions}/{id}/merge` → `{target_id}`.
- `POST /api/admin/imports/{id}/bulk-approve` → `{min_confidence, type: concepts|questions|all}`.
- `GET  /api/topics/{id}/concepts` — public (auth required) — list concepts for a topic.
- Admin CRUD for `topic_concepts`: `POST /api/admin/concepts`, `PUT /api/admin/concepts/{id}`, `DELETE /api/admin/concepts/{id}`.

#### Async pipeline (FastAPI BackgroundTasks for v1; Celery later if cost demands it)
1. PDF → page splitter (`PyMuPDF`).
2. Each page → 300 DPI image — Gemini Nano Banana handles vision directly (better fidelity on math, tables, hand-written content than text-extraction).
3. Page image → Gemini prompt: *"Extract every key-concept section AND every question on this page as JSON matching this schema…"* Use **structured output** (`response_mime_type: application/json`).
4. For each extracted item → second Gemini call with syllabus-aware classifier: *"Given the GATE CSE syllabus [...], assign subject_id and topic_id."*
5. Duplicate detection (text-hash now, embeddings later).
6. Update `pdf_imports.processed_pages` per page so the UI can show progress.

#### Prompt assets (`backend/prompts/`)
- `ocr_extract.md` — extracts both concepts and questions in one call.
- `topic_classify.md` — full syllabus tree as context, regenerated from DB at startup.

#### Concurrency & cost
- Rate-limit Gemini calls (env var, default 2/sec) with exponential backoff on 429.
- Track per-import cost estimate; surface in the admin UI before kicking off ("estimated cost: $X").
- Hard daily budget cap per user.

#### Frontend
- **`pages/AdminImports.jsx`** — list of imports with status pills.
- **`pages/AdminImportReview.jsx`** — two tabs: **Concepts** | **Questions**. Each tab is a paginated table with inline editors and bulk-approve toolbar.
- **`components/QuestionEditor.jsx`** — reusable (used here + in Phase 6 edit flow).
- **`components/ConceptEditor.jsx`** — reusable.
- **`pages/TopicDetail.jsx`** — add a **"Key Concepts"** section above the Open QBank / Open PYQs buttons:
  - Stacked accordion of concepts, ordered by `position`.
  - Each concept card: title + KaTeX-rendered markdown + source attribution footer.
  - Admin-only inline edit / delete.
  - Empty state encourages admin to run the importer.

#### One-shot importer CLI
`backend/scripts/import_go_pdfs.py`:
1. Hits GitHub API for latest release tag of `GATEOverflow/GO-PDFs`.
2. Downloads all PDFs to `backend/data/go_pdfs/`.
3. POSTs each to `/api/admin/imports/pdf` using an admin JWT.
4. Polls progress endpoints.
5. Prints a final summary table:
   ```
   PDF                              pages   concepts   questions   duplicates
   GATE-CSE-1987-2024.pdf            520        0          3210         42
   Digital-Logic-v4.pdf               85       28           120          7
   ...
   ```

### Risks & mitigations
| Risk | Mitigation |
|---|---|
| Gemini hallucinates options / answers | Confidence + mandatory review queue; nothing auto-commits. |
| Concept boundaries are fuzzy (where does one concept end and the next begin?) | Provide the model with explicit page-layout cues + topic taxonomy; tune prompt iteratively on Reconnaissance Day output. |
| Large PDFs blow up memory | Process page-by-page; stream from disk. |
| Gemini cost runaway | Per-user daily quota; show pre-flight estimate; rate-limit. |
| Duplicate detection misses paraphrases | Two-layer: exact hash + embedding cosine. Threshold tuned after first 500 imports. |
| Math-heavy concepts/questions extract poorly | Vision-first (send images, not extracted text); KaTeX rendering (Phase 7) closes the display loop. |
| GO-PDFs license drift | Store `source` + `source_url` on every imported item; display "from GateOverflow" attribution badge in the UI. |

### Acceptance criteria
- [ ] Reconnaissance doc filed: sample of 3 GO-PDFs analysed, structure documented.
- [ ] `topic_concepts` collection exists with the schema above.
- [ ] `GET /api/topics/{id}/concepts` returns concepts in `position` order.
- [ ] TopicDetail page renders a Key Concepts section with KaTeX (or graceful fallback if Phase 7 hasn't shipped yet).
- [ ] Admin can upload a real GATE PYQ PDF and end up with ≥ 80% of questions extracted correctly.
- [ ] Admin can upload a real GO topic-wise PDF and end up with key concepts in the review queue, mapped to the right topic ≥ 80% of the time.
- [ ] Confidence ≥ 0.85 items are correct ≥ 90% of the time on a 50-item sample.
- [ ] Bulk approve works for both concepts and questions queues independently.
- [ ] One-shot importer CLI runs end-to-end on the latest GO-PDFs release without manual intervention.
- [ ] Every imported item carries `source` + `source_url`.
- [ ] No Gemini call without an explicit admin action.

### Estimated effort
**17–22 engineer-days** (vs. the original 8–12 for questions-only). The concept-handling roughly doubles Phase 5's scope, but you get the full GO-PDFs corpus — concepts + questions + PYQs since 1987 — in one pipeline.

### Sequencing within Phase 5
1. **Day 0:** Reconnaissance (manual). Download 3 PDFs, document structure, refine the OCR prompt against reality.
2. **Day 1–2:** `topic_concepts` collection + admin CRUD + TopicDetail UI section (concept-display path works before extraction even exists).
3. **Day 3–6:** Pipeline scaffolding — `pdf_imports`, `extracted_concepts`, `extracted_questions`, async task runner, single-PDF upload endpoint.
4. **Day 7–10:** Gemini prompt engineering — single-call dual-output structured JSON; topic classifier prompt; duplicate detection (hash layer first).
5. **Day 11–14:** Two review queue UIs (Concepts tab + Questions tab) with inline editors + bulk approve.
6. **Day 15–16:** GitHub-release downloader CLI.
7. **Day 17–18:** End-to-end dry run on one topic-wise PDF + one PYQ PDF; tune prompts + thresholds.
8. **Day 19–22:** Full bulk import → admin reviews → backfill of the entire corpus.

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
| 1    | **Reconnaissance** + `topic_concepts` collection + TopicDetail "Key Concepts" UI section |
| 2–4  | **Phase 5** — OCR Pipeline (concepts + questions) + Review Queue UIs |
| 4    | **GO-PDFs CLI importer** + first end-to-end dry run              |
| 5    | **Bulk import** of full GO-PDFs corpus → admin review + bulk-approve |
| 5    | **Phase 7 (partial)** — KaTeX rendering for concepts + solutions (prerequisite for displaying imported content well) |
| 6    | **Phase 6** — Pagination, edit, CSV bulk                         |
| 6+   | **Smart Today's Plan** + **Streak** (from Suggestions §2 & §4)   |

Re-evaluate after Week 6 against real-user feedback.

---

<p align="center">
  <em>Plans are worthless. Planning is everything. — Eisenhower</em>
</p>
