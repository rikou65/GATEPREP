# GATE Study OS — Product Requirements Doc

**Last updated:** June 2026
**Status:** Phase 5 (OCR Pipeline) core complete. Active priorities: OCR image extraction, Vite migration.

---

## 1. Original problem statement

Build a multi-tenant **Study Operating System** for GATE CSE preparation — a personal study tool, *not* a coaching platform, *not* a social network, *not* a leaderboard. Users bring their own questions, PYQs, video playlists, notes, and resources, and the system tracks measurable progress against the **official GATE CSE syllabus** (12 subjects → topics).

The product should feel like a calm, focused Notion-like surface, telling the user *what to study next* based on signal, not vibes.

---

## 2. Core architecture

- **Backend:** FastAPI (Python 3.12) + Motor (async MongoDB) + Pydantic v2. All routes prefixed `/api`.
- **Frontend:** React 19 + react-router-dom 7 + Tailwind + shadcn/ui (dark theme) + axios + `pdfjs-dist` + `mathFormat.jsx`.
- **Database:** MongoDB. Every user-owned collection scoped by `user_id` (multi-tenant from line 1).
- **Auth:** Standard Google OAuth (Code Exchange) → JWT session tokens.
- **Google Drive:** *Separate* OAuth client with `drive.file` scope — user's files live in their own Drive under `GATEPREP/{Type}/{Subject}/`.
- **YouTube:** Data API v3 for playlist imports; IFrame API for inline playback + progress tracking.
- **OCR/AI:** Mistral AI — `mistral-ocr-latest` for raw text extraction, `mistral-large-latest` for structured question/solution/concept parsing via `client.chat.parse`.
- **LLM (planned):** Gemini via Gemini API for conversational features (Phase exploratory backlog).

---

## 3. Strict product rules (non-negotiable)

1. **No combined subject completion %.** Per-topic *Solved / Remaining / Accuracy* only.
2. **QBank and PYQ tracked separately.** Two collections, two analytics tracks. Never aggregated.
3. **Accuracy uses only the latest attempt per question.** Re-attempting a wrong question fully overwrites the failure.
4. **Inline solutions** — never modals.
5. **Multi-tenant by `user_id`** on every read and write.
6. **Files belong to the user.** Drive storage is `drive.file` scoped; we only see what we create.
7. **PDFs render via `pdfjs-dist` on a canvas** — never via Drive iframe (Brave/Chrome cookie blocks).
8. **PDF viewer keeps the sidebar visible** (modal mounted to body but offset `lg:left-64`).
9. **Playlists attached to subjects, not topics** (YouTube playlists cross topic boundaries in reality).
10. **No `difficulty` field.** Removed permanently. Difficulty is subjective and user-specific. Users may use the `tags` array on questions if they wish to self-classify.
11. **No hardcoded source tags.** Source (publisher/series name) is declared by the user at upload time. Never defaulted in code.
12. **Math always rendered.** All question text and option text must go through `formatMathText()` or `renderContentWithTables()` before display. Raw LaTeX strings must never appear as plain text to the user.

---

## 4. Implemented (cumulative)

### Auth & users
- `/api/auth/session`, `/api/auth/me`, `/api/auth/logout` (cookie + Bearer).
- **Dev-Bypass:** `POST /api/auth/dev-login` for instant local access without Google (Demo Student).

### Syllabus
- 12 official GATE CSE subjects seeded.
- Topic taxonomy aligned to official syllabus.
- Subjects ↔ Topics navigable with rich stats.

### Question Bank
- MCQ / MSQ / NAT with proper UX (radio / multi-select / numeric tolerance).
- Filters: subject, topic, type. (High-performance DB aggregation).
- Inline solutions revealed after submit.
- Per-user attempt logging in `question_attempts`.
- Subject + topic tags rendered on each question card.
- URL params `?subject_id=&topic_id=` pre-populate filters.
- Notes per question (auto-save).
- **Math rendering:** question text, options, and solution text all rendered via `mathFormat.jsx`.
- **Topic badge:** displayed from extracted section heading (e.g. "Boolean Algebra").

### PYQs
- Parallel collection to questions, independent analytics.
- **Year filter dropdown** (2000–2026) with refined UI alignment.
- Same subject+topic tag rendering.

### Mistake Lab
- Auto-populated from incorrect attempts (questions + PYQs).
- Filter by subject + mistake type (Conceptual Gap / Calculation Error / Question Misread / Silly Mistake).
- Manual delete to "resolve".

### Playlists
- YouTube playlist URL → import via YT Data API (title, thumbnails, full video list, durations).
- Grouped by subject.
- Inline IFrame playback with progress tracking (≥ 90% watched = completed).

### Resources (Google Drive)
- OAuth `drive.file` connect / disconnect flow.
- Auto-provisioned folder hierarchy in user's Drive: `GATEPREP/{PDF|Notes|Other}/{Subject}/`.
- Upload streams through backend → pushes to Drive → stores metadata only.
- **Sync from Drive** — re-scan `GATEPREP/` and re-attach Drive files into the local DB.
- **Per-resource study notes** (free-form text, auto-saved with 600ms debounce).
- **Important pages** — flag/label/jump bookmarks inside PDF viewer.
- **Inline PDF viewer** via custom `PdfCanvasViewer.jsx` (windowed rendering, multi-page scroll).
- **Streaming Proxy:** Backend acts as chunked pipe from Drive to browser for memory efficiency.

### Dashboard
- 8 top-level stat cards (Questions, PYQs, Accuracy, etc.).
- **Subject HUD card grid**: each subject card has 2 horizontal progress bars (QBank + PYQ).
- Color-coded by accuracy (emerald ≥75% / amber ≥50% / red <50%).

### Subject detail page
- **2-column topic card grid**.
- Each topic card: name + 2 metric blocks (QBank, PYQ) showing `solved/total`.

### Admin (Autonomy Model)
- **Admin role retired.** Every authenticated user owns and manages their own bank.
- Add/Edit/Delete Question & PYQ UI available to all signed-in users.

### Analytics (Performance)
- All analytics offloaded to **MongoDB Aggregation Pipelines**.
- Instantly handles 5,000+ items without Python overhead.

### PDF OCR Pipeline — Phase 5 (Core Complete)

**Import PDF page (`/admin/import`):**
- Engine: Mistral AI only (LlamaAI option removed).
- Source / Publisher field — user declares source at upload time (e.g. "GO-PDFs", "MADE Easy").
- Subject selection maps OCR output to the correct DB subject.

**Pipeline (`backend/scripts/mistral_ocr.py`):**
- PDF sliced into 5-page chunks via `pypdfium2`.
- Each chunk uploaded to Mistral Files API → OCR'd via `mistral-ocr-latest` → markdown extracted.
- Markdown parsed via `mistral-large-latest` `client.chat.parse` with strict verbatim extraction prompt.
- Returns `CombinedPassResponse`: lists of `ExtractedQuestion`, `ExtractedSolution`, `ExtractedConcept`.
- Env safety: reads `MISTRAL_API_KEY` from `os.environ.get()` directly — never from `settings` Pydantic object (background task worker context issue).

**Stitch & Upsert (`_stitch_and_save`):**
- `normalize_id()` strips `Q.` prefix so `Q.1`, `Q1`, `1` all resolve to `"1"` before every lookup.
- Questions and solutions merged by normalized ID — prevents 130 records from 65-question PDF.
- Status: `READY` (both question + solution present), `ORPHANED_QUESTION`, `ORPHANED_SOLUTION`.

**Staging Queue (`/admin/staging`):**
- Live progress bar per active job (auto-poll every 5s).
- READY items: question text + options with full math rendering.
- Orphan items: separate "Action Required" section with Force Approve / Discard.
- **Approve All 100% Matches** — bulk-approves all READY items.
- **🗑 Clear All** — wipes entire staging collection for a clean re-run.
- **✕ Dismiss on failed jobs** — deletes job record from DB, error box disappears immediately.
- Math rendered via `formatMathText()` on all question text, option text in both sections.

**Known limitation — images:**
- Mistral structured extraction does not embed base64 image data.
- Circuit diagrams render as `📐 [Figure Description]` placeholder chips.
- Fix planned in Phase 5 continued (see `IMPLEMENTATION_PLAN.md`).

**Approve flow:**
- No `difficulty` tag injected. No hardcoded `source` tag.
- `topic` from PDF section heading, `source` from user's upload-time input.
- Question goes into live `questions` collection on approval.

---

## 5. Active backlog (prioritized)

### 🔴 P0 — Active

- **OCR Image Extraction:** Capture `page.images` base64 data from raw Mistral OCR response. Store in `ocr_images` collection. Serve via `/api/admin/ocr-images/{id}`. Render as `<img>` in `mathFormat.jsx`.

### 🟡 P1 — Next

- **Vite Migration:** Replace CRA with Vite. Cold-start drops from ~50s to <1s. HMR instant. See `IMPLEMENTATION_PLAN.md` Phase 6.
- **Full KaTeX Integration:** Replace `mathFormat.jsx` custom renderer with official KaTeX library.
- **Pagination:** Cursor-based pagination on Question Bank and PYQs at 50 items/page.
- **Global Search (Cmd+K):** MongoDB text index + unified search overlay.
- **MongoDB Indexes:** Compound indexes on `(subject_id, topic)` and `(user_id, status)`.

### 🟢 P2 — Later

- **SM-2 Spaced Repetition** in Mistake Lab.
- **Mock Test Mode** — timed, GATE-style, negative marking, auto-submit.
- **Redis Caching** — dashboard aggregation TTL cache.
- **Backend Route Splitting** — `server.py` into `routes/` sub-modules.
- **PWA / Offline** — service worker for PDF reader.

---

## 6. Known issues / active blockers

- **Circuit diagram images** show as placeholders — root cause documented above; fix in P0.
- **CRA startup time** — 30–60 seconds cold start; fix is Vite migration (P1).
- `server.py` is monolithic — refactor scheduled post-Phase 6.
- Drive sync latency for massive folders (no fix planned — streaming proxy already addresses this).

---

## 7. Changelog (June 2026)

| Change | Status |
|---|---|
| **Mistral OCR Pipeline** (verbatim extraction, 5-page chunks) | ✅ Shipped |
| **ID Normalization** (`Q.1` / `1` → same record, no duplicates) | ✅ Shipped |
| **Source field on Import PDF** (user-declared, no default) | ✅ Shipped |
| **Topic auto-detection** from PDF section headings | ✅ Shipped |
| **Difficulty tag removed** from all flows permanently | ✅ Shipped |
| **Staging Queue — live progress bar** (5s auto-refresh) | ✅ Shipped |
| **Staging Queue — Clear All button** | ✅ Shipped |
| **Failed job — dismissible error box** (✕ → deletes from DB) | ✅ Shipped |
| **Math rendering in staging** (options + question text) | ✅ Shipped |
| **LlamaAI import option removed** (Mistral only) | ✅ Shipped |
| **MongoDB Aggregation Fix** (high-speed analytics) | ✅ Shipped |
| **StreamingResponse** (100MB+ file memory safety) | ✅ Shipped |
| **Admin Role Retired** (every user is their own admin) | ✅ Shipped |
| **Year dropdown** (2000–2026 for PYQs) | ✅ Shipped |
| **Local Login Bypass** (dev mode student) | ✅ Shipped |
| **Google OAuth Code Flow** (reliable auth) | ✅ Shipped |

---

## 8. Test credentials

See `test_credentials.md` in this repo (if present).
