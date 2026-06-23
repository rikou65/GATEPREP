# GATE Study OS — Product Requirements Doc

**Last updated:** Feb 2026
**Status:** MVP shipped; OCR + GO-PDFs ingestion is the next major build.

---

## 1. Original problem statement

Build a multi-tenant **Study Operating System** for GATE CSE preparation — a personal study tool, *not* a coaching platform, *not* a social network, *not* a leaderboard. Users bring their own questions, PYQs, video playlists, notes, and resources, and the system tracks measurable progress against the **official GATE CSE syllabus** (12 subjects → topics).

The product should feel like a calm, focused Notion-like surface, telling the user *what to study next* based on signal, not vibes.

---

## 2. Core architecture

- **Backend:** FastAPI (Python 3.12) + Motor (async MongoDB) + Pydantic v2. All routes prefixed `/api`.
- **Frontend:** React 19 + react-router-dom 7 + Tailwind + shadcn/ui (dark theme) + axios + recharts + `pdfjs-dist`.
- **Database:** MongoDB. Every user-owned collection scoped by `user_id` (multi-tenant from line 1).
- **Auth:** Standard Google OAuth (Code Exchange) → JWT session tokens.
- **Google Drive:** *Separate* OAuth client with `drive.file` scope — user’s files live in their own Drive under `GATEPREP/{Type}/{Subject}/`.
- **YouTube:** Data API v3 for playlist imports; IFrame API for inline playback + progress tracking.
- **LLM (planned):** Gemini 1.5 Flash via Gemini API Key for OCR ingestion.

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
- Auto-provisioned folder hierarchy in user’s Drive: `GATEPREP/{PDF|Notes|Other}/{Subject}/`.
- Upload streams through backend → pushes to Drive → stores metadata only.
- **Sync from Drive** — re-scan `GATEPREP/` and re-attach Drive files into the local DB.
- **Per-resource study notes** (free-form text, auto-saved with 600ms debounce).
- **Important pages** — flag/label/jump bookmarks inside PDF viewer.
- **Inline PDF viewer** via custom `PdfCanvasViewer.jsx` (Windowed rendering, multi-page scroll).
- **Streaming Proxy:** Backend acts as chunked pipe from Drive to browser for memory efficiency.

### Dashboard
- 8 top-level stat cards (Questions, PYQs, Accuracy, etc.).
- **"Question Bank vs PYQ progress" — card grid**:
  - Each subject card has 2 horizontal progress bars.
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

---

## 5. Documented but NOT yet implemented (the active backlog)

### 🔴 P0 — PDF Import + OCR Pipeline (Phase 5)
Source: `GATEOverflow/GO-PDFs`. Gemini-powered extraction of:
1. **Key concept sections** (LaTeX content)
2. **Questions** (Structured JSON)

**Staging area:** Two parallel review queues for human approval before committing to bank.

### 🟡 P1
- Pagination on Question Bank + PYQs.
- Global Search (Cmd+K).
- System-wide **KaTeX rendering** for high-fidelity math.

### 🟢 P2
- **Spaced-repetition Mistake Lab** (SM-2 implementation).
- Mock test mode (timed, GATE-style marking).

---

## 6. Known issues / active blockers

- **Drive Connection Blockage:** The "Failed to start Drive connection" popup is currently persisting. 
  - *Current State:* Refactored to Manual OAuth exchange (no PKCE).
  - *Redirects:* Using `http://127.0.0.1` for local consistency.
  - *Required Config:* 4 URIs must be in Console (localhost/127.0.0.1 for ports 3000/8000).
- `server.py` is monolithic (Refactor scheduled post-Phase 5).
- Drive sync latency for massive folders.

---

## 7. Recent user-driven changes (Feb 2026)

| Change | Status |
|---|---|
| **MongoDB Aggregation Fix** (High-speed analytics) | ✅ Shipped |
| **StreamingResponse** (100MB+ file memory safety) | ✅ Shipped |
| **Admin Role Retired** (Every user is their own Admin) | ✅ Shipped |
| **Year dropdown** (2000-2026 dropdown for PYQs) | ✅ Shipped |
| **Filter alignment** (pl-3 / right-12px design) | ✅ Shipped |
| **Local Login Bypass** (Dev Mode Student) | ✅ Shipped |
| **Google OAuth Code Flow** (Reliable auth) | ✅ Shipped |

---

## 8. Test credentials

See [`memory/test_credentials.md`](./test_credentials.md).
