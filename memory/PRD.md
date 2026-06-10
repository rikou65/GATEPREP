# GATE Study OS — Product Requirements Doc

**Last updated:** Feb 2026
**Status:** MVP shipped; OCR + GO-PDFs ingestion is the next major build.

---

## 1. Original problem statement

Build a multi-tenant **Study Operating System** for GATE CSE preparation — a personal study tool, *not* a coaching platform, *not* a social network, *not* a leaderboard. Users bring their own questions, PYQs, video playlists, notes, and resources, and the system tracks measurable progress against the **official GATE CSE syllabus** (12 subjects → topics).

The product should feel like a calm, focused Notion-like surface, telling the user *what to study next* based on signal, not vibes.

---

## 2. Core architecture

- **Backend:** FastAPI (Python 3.11) + Motor (async MongoDB) + Pydantic v2. All routes prefixed `/api`.
- **Frontend:** React 19 + react-router-dom 7 + Tailwind + shadcn/ui (dark theme) + axios + recharts + `pdfjs-dist`.
- **Database:** MongoDB. Every user-owned collection scoped by `user_id` (multi-tenant from line 1).
- **Auth:** Emergent-managed Google OAuth → JWT session tokens.
- **Google Drive:** *Separate* OAuth client with `drive.file` scope — user’s files live in their own Drive under `GATEPREP/{Type}/{Subject}/`.
- **YouTube:** Data API v3 for playlist imports; IFrame API for inline playback + progress tracking.
- **LLM (planned):** Gemini Nano Banana via Emergent Universal LLM key for OCR ingestion.

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
- `/api/auth/session`, `/api/auth/me`, `/api/auth/logout` (cookie + Bearer)
- First user auto-promoted to admin; subsequent admins set via `ADMIN_EMAILS` env or DB toggle.

### Syllabus
- 12 official GATE CSE subjects seeded.
- Topic taxonomy aligned to official syllabus.
- Subjects ↔ Topics navigable with rich stats.

### Question Bank
- MCQ / MSQ / NAT with proper UX (radio / multi-select / numeric tolerance).
- Filters: subject, topic, type. **Difficulty filter removed** (badge stays on the question, but it’s not a filter axis).
- Inline solutions revealed after submit.
- Per-user attempt logging in `question_attempts`.
- **Subject + topic tags** rendered on each question card (alongside MCQ/Easy/year tags).
- URL params `?subject_id=&topic_id=` pre-populate filters (sync’d via `useEffect` on `useSearchParams`).
- Notes per question (auto-save).
- Attempt history endpoint.

### PYQs
- Parallel collection to questions, independent analytics.
- Year filter. Same UX as Question Bank.
- Same subject+topic tag rendering.
- Same URL-param sync.

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
- **Inline PDF viewer** via custom `PdfCanvasViewer.jsx`:
  - Continuous multi-page scroll with mouse wheel.
  - Windowed rendering (only ±2 pages around viewport render canvas; rest are lightweight placeholders) — handles 200+ page PDFs without melting the browser.
  - Sticky dark-themed toolbar: page navigation, direct page input, zoom in/out, fit-to-width toggle.
  - Keyboard shortcuts (←/→, PageUp/Down, Esc).
  - Portal-mounted modal with `lg:left-64` offset so sidebar stays visible.
  - `dark` class scoped on portal so Tailwind dark vars resolve correctly.
  - In-session blob cache (no re-downloads when reopening the same PDF).
- Streaming endpoint (`/api/resources/{id}/stream`) uses user’s Drive refresh token — bypasses Brave/Chrome third-party-cookie iframe blocks.

### Dashboard
- 8 top-level stat cards (questions solved, PYQs solved, videos completed, playlists, QB accuracy, PYQ accuracy, mistakes, resources).
- **"Question Bank vs PYQ progress" — card grid** (replaced the old sparse table):
  - 1 / 2 / 3 column responsive grid.
  - Each subject card has 2 horizontal progress bars (QBank, PYQ).
  - Color-coded by accuracy (emerald ≥75% / amber ≥50% / red <50% / muted if no attempts).
  - Whole card is a link to subject detail.

### Subject detail page
- Redesigned from the old 8-column table → **2-column topic card grid**.
- Each topic card: name + 2 metric blocks (QBank, PYQ) showing `solved/total`, color-coded accuracy, "X left / all done / no items yet" footer.
- Notes count + "X to revisit" badge strip when non-zero.
- Whole card is the topic link.

### Admin
- Add Question / PYQ forms.
- Subjects + Topics CRUD.
- Users list (role gated).

### Analytics
- Per-subject + per-topic analytics endpoints.
- recharts visualisations.

### Backend hygiene
- Cyclomatic complexity reduced on `dashboard()`, `import_playlist()`, `seed_data()` helpers.
- Pytest suite at `backend/tests/test_gate_os_backend.py`.

---

## 5. Documented but NOT yet implemented (the active backlog)

### 🔴 P0 — PDF Import + OCR Pipeline, now scoped to **GO-PDFs ingestion**

**Source of truth:** `GATEOverflow/GO-PDFs` on GitHub. The GO admins publish a comprehensive, free, attribution-licensed PDF set: every GATE CSE PYQ since 1987 + topic-wise volumes (Eng Math, Discrete Math, DSA, OS, DBMS, CN, COA, TOC, Compilers, Digital Logic, Algorithms, Aptitude) that contain **both key concepts and questions**.

**New scope addition vs. original plan:** OCR must now extract **two content types** per page:
1. **Key concept sections** (title + content with LaTeX, no options/answer)
2. **Questions** (with options, correct answer, solution)

**New entity:** `topic_concepts` collection:
```
concept_id, topic_id, subject_id, title, content_markdown,
position, source, source_url, created_at, updated_at
```

**Two parallel review queues** in Admin:
- `extracted_concepts` → reviewed → `topic_concepts`
- `extracted_questions` → reviewed → `questions` / `pyqs`

**End deliverable:** One-shot CLI (`backend/scripts/import_go_pdfs.py`) that downloads the latest release tag and runs every PDF through the pipeline. Admin reviews + bulk-approves.

**Estimated effort:** 17–22 engineer-days (vs. 8–12 for questions-only).

### 🟡 P1
- Pagination on Question Bank + PYQs.
- Question/PYQ editing in Admin.
- Bulk CSV upload for Questions/PYQs.
- Global Search (Cmd+K).
- KaTeX math rendering (`MathText.jsx` component) — *prerequisite* for Phase 5 since both concepts and solutions contain LaTeX.
- Topic Concepts UI on TopicDetail page (depends on `topic_concepts` collection).

### 🟢 P2
- Spaced-repetition Mistake Lab (SM-2).
- Mock test mode (GATE-style 65q/180min with negative marking).
- Backend refactor: split `server.py` into `routes/` + `services/`.

### 💭 Exploratory
- AI Study Partner (Gemini conversational tutor).
- Streak + Daily Goal + Smart "Today's Plan".
- PYQ Trend Analyzer.
- Calibration diagnostic quiz onboarding.

Full detail in [`IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md).

---

## 6. Known issues / accepted debt

- `server.py` is ~1.4k LOC monolithic. Refactor scheduled but **not yet triggered** (waiting for ~2k LOC or contributor conflict).
- Static analyzer false-positives `is None` PEP-8 checks — ignored intentionally.
- React 19's `set-state-in-effect` ESLint rule flags standard fetch-into-state patterns — false positive, ignored.
- No spaced repetition yet; mistakes are FIFO until Phase 8A.

---

## 7. Recent user-driven changes (Feb 2026)

| Change | Status |
|---|---|
| Accuracy counts only the **latest attempt per question** | ✅ Shipped |
| **Subject + topic tags** on every question card | ✅ Shipped |
| **Difficulty filter removed** from QBank/PYQs | ✅ Shipped |
| Topic → QBank/PYQ link **pre-fills both subject + topic** filters | ✅ Shipped |
| SubjectDetail UI redesigned (table → card grid) | ✅ Shipped |
| Dashboard "By Subject" UI redesigned (table → progress-bar cards) | ✅ Shipped |
| PdfCanvasViewer: continuous scroll + windowed render + sidebar visible + dark theme | ✅ Shipped |
| **Key Concepts feature + GO-PDFs ingestion plan** | 📋 Documented (this update) |

---

## 8. Test credentials

See [`memory/test_credentials.md`](./test_credentials.md).
