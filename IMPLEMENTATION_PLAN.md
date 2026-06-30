# GATEPREP — Implementation Plan

> A pragmatic, sequenced engineering plan for GATEPREP. Re-prioritise at the start of each week.

---

## ✅ Phase 1: MVP Hardening (Completed)
- **High-Performance Analytics:** Moved accuracy and progress logic into MongoDB Aggregation Pipelines to support 5,000+ questions.
- **Memory-Safe Resources:** Implemented `StreamingResponse` for chunked PDF delivery (No server memory crashes).
- **Manual OAuth Fix:** Implemented direct code-for-token exchange for both Login and Drive to resolve PKCE/Verifier errors.
- **De-branding:** Completely removed all Emergent AI branding and replaced with a clean, personal UI.

---

## ✅ Phase 2: User Autonomy & Scaling (Completed)
- **Admin Role Retirement:** Removed `require_admin` gatekeeping. Every user manages their own bank.
- **Library Polish:** Added descending Year Dropdown (2026–2000) and perfected filter alignment.
- **Dev-Bypass:** Added local demo login for instant testing without external dependencies.
- **Multi-tenant Indexing:** Verified `user_id` scoping on all CRUD operations.

---

## ✅ Phase 5: PDF Import & OCR Pipeline (Completed — Core)

*Mistral AI-powered bulk ingestion of GATE study material PDFs.*

### Goal: Ingest questions and concepts from any GATE study PDF verbatim.

#### What was built:

1. **Mistral OCR Pipeline (`backend/scripts/mistral_ocr.py`):**
   - PDF is sliced into **5-page chunks** using `pypdfium2` before upload.
   - Each chunk is uploaded to Mistral Files API and processed with `mistral-ocr-latest` to get raw markdown.
   - Markdown is passed to `mistral-large-latest` via `client.chat.parse` with a strict Pydantic schema (`CombinedPassResponse`) containing `questions`, `solutions`, and `concepts` lists.
   - Extraction prompt enforces **strict verbatim** copying — no paraphrasing, no summarizing.
   - Each question carries: `extracted_id`, `question_text`, `options`, `topic`, `question_type`, `is_pyq`, `year`, `gate_set`, `gate_qnum`.
   - Each solution carries: `target_id`, `correct_answer`, `solution_text`.

2. **ID Normalization (`normalize_id`):**
   - PDFs typically label questions as `Q.1`–`Q.65` and solutions as `1`–`65`.
   - Without normalization these become 130 separate orphaned records instead of 65 complete ones.
   - `normalize_id()` strips the leading `Q.` prefix so `Q.1`, `Q1`, and `1` all resolve to `"1"` before every DB lookup and insert.

3. **Incremental Stitch & Upsert:**
   - On each chunk's completion, questions and solutions are merged by normalized ID.
   - If a question arrives before its solution: stored as `ORPHANED_QUESTION`.
   - If a solution arrives before its question: stored as `ORPHANED_SOLUTION`.
   - When both are present: status upgrades to `READY` automatically.

4. **Source Tagging at Upload Time:**
   - Import PDF page has a **Source / Publisher** text field (e.g. "GO-PDFs", "MADE Easy", "ACE Academy").
   - Source is passed through `POST /api/admin/import/pdf` → stored in `import_jobs` and every staging document → carried into live `questions` collection on approval.
   - No hardcoded default. Blank if not provided.

5. **Topic Auto-detection:**
   - The extraction prompt instructs Mistral to identify the nearest section heading above each question (e.g. "Boolean Algebra", "Sequential Circuits").
   - Stored as `topic` field on both staging and approved question documents.
   - Displayed as a badge on `QuestionViewer` and `StagingQueue`.

6. **No Difficulty Tag:**
   - `difficulty` field is **completely removed** from all approve flows, staging docs, and `QuestionViewer` display.
   - Difficulty is subjective. Users can express it via the `tags` array if they choose.

7. **Staging Queue UI (`frontend/src/pages/StagingQueue.jsx`):**
   - Live progress bar per active job (auto-refreshes every 5 seconds).
   - READY items show question text + options with math rendered.
   - Orphan items (missing question or solution) shown in a separate "Action Required" section.
   - Per-item **Approve** / **Discard** buttons.
   - **Approve All 100% Matches** — bulk-approves all READY items.
   - **🗑 Clear All** — wipes the entire staging collection for a clean re-run.
   - **✕ Dismiss** on every failed job error box — removes the job record from DB permanently, error box disappears immediately.

8. **Math Rendering (`frontend/src/lib/mathFormat.jsx`):**
   - Shared utility used by both `StagingQueue` and `QuestionViewer`.
   - Handles `$...$` inline math, `$$...$$` display math, `![alt](src)` image placeholders.
   - Processes `\bar{X}`, `\overline{X}`, `\frac{a}{b}`, `_{sub}`, `^{sup}`, and 30+ symbol replacements (`\oplus` → ⊕, `\Sigma` → Σ, etc.).
   - Applied to both question text and option text in staging and live question view.

9. **Backend Env Safety:**
   - `mistral_ocr.py` reads `MISTRAL_API_KEY` via `os.environ.get()` directly.
   - This avoids the `name 'settings' is not defined` error that occurred when background tasks were spawned in a worker context where the Pydantic `settings` singleton was not yet initialized.

#### Known Limitation — Circuit Diagram Images:
- Mistral OCR returns image references like `![Figure](img-4.jpeg)` in markdown.
- The structured extraction pass does not embed base64 image data.
- These render as `📐 [Figure Description]` placeholder chips in the UI.
- **Fix is planned in Phase 5 continued** (see below).

---

## 🔴 Phase 5 (Continued): OCR Image Extraction (Active)

*Circuit diagrams are currently placeholder chips. This phase makes them real.*

### Plan:
1. After each OCR chunk completes, inspect `ocr_response.pages[n].images` — Mistral returns base64 image data here in the raw response.
2. Store each image as a document in a new `ocr_images` collection: `{ image_id, job_id, page, base64, mime_type }`.
3. When saving staging questions, replace `img-N.jpeg` references with `{ image_id }` references.
4. Serve images via a new endpoint `GET /api/admin/ocr-images/{image_id}` that returns the base64 as `image/png`.
5. Update `mathFormat.jsx` to render `![alt](image_id)` as an `<img>` tag fetching from that endpoint.

---

## 🟡 Phase 6: Frontend Performance — Vite Migration (Next)

*CRA cold-start is 30–60 seconds. Vite makes it under 1 second.*

### Why migrate:
- CRA bundles the entire app on every cold start even in development.
- Vite uses native ES modules — it serves files as-is and only transforms on request.
- HMR (Hot Module Replacement) with Vite is near-instant vs. CRA's multi-second rebuilds.
- Vite's production build (Rollup) produces significantly smaller bundles than CRA's webpack output.

### Migration steps:
1. `npm create vite@latest frontend-vite -- --template react` in a temp dir.
2. Move `src/`, `public/` over.
3. Replace `craco.config.js` path aliases with `vite.config.js` resolve aliases.
4. Rename all `REACT_APP_*` env vars to `VITE_*` and update `import.meta.env.VITE_*` references in code.
5. Replace `react-scripts` scripts in `package.json` with `vite` / `vite build` / `vite preview`.
6. Test Drive, PDF viewer, YouTube player, and OCR staging queue after migration.
7. Update `SELF_HOSTING.md` Vercel build settings (`npm run build` → same, output dir `dist` not `build`).

---

## 🟡 Phase 7: Math & Search (Next)

*Full KaTeX coverage and Cmd+K unified search.*

1. **Full KaTeX Integration:**
   - Replace `mathFormat.jsx` custom renderer with the official `katex` or `react-katex` library.
   - Covers 100% of LaTeX: `\int`, `\lim`, `\sum_{i=0}^{n}`, matrices, multi-line `align` environments.
   - `mathFormat.jsx` will remain as a thin wrapper that calls KaTeX for `$...$` blocks.
   - Add `katex/dist/katex.min.css` to `index.css` import chain.

2. **Global Search (Cmd+K):**
   - MongoDB `$text` index on `question_text` + `topic` in both `questions` and `pyqs` collections.
   - Unified search bar overlay (Cmd+K / Ctrl+K) covering Subjects, Topics, Resources, and Questions.
   - Debounced 300ms API call to `GET /api/search?q=` with results grouped by type.

3. **Pagination:**
   - Cursor-based pagination on Question Bank and PYQs at 50 items per page.
   - Backend: `find().skip(offset).limit(50)` with a `next_cursor` in response.
   - Frontend: "Load more" button or infinite scroll.

---

## 🟡 Phase 8: Spaced Repetition (Upcoming)

*Transforming the Mistake Lab into a retention engine.*

1. **SM-2 Core:** Implement the SuperMemo-2 scheduling algorithm.
   - Store `ease_factor`, `interval_days`, `next_review_at` per `(user_id, question_id)`.
   - After each review session, update ease factor based on response quality (0–5 scale).
2. **Dynamic Review:** Re-order Mistake Lab by `next_review_at` — overdue items surface first.
3. **Outcome Tracking:** Distinguish "reviewed and got it" from "reviewed and failed again" — the latter resets the interval.

---

## 🟢 Phase 9: Performance & Scale

*Engineering headroom for 10,000+ questions and multiple users.*

1. **Redis Caching:**
   - Cache dashboard aggregation results and subject analytics with a 5-minute TTL.
   - Invalidate on new question_attempt or question insert.
   - Use `redis-py` async client alongside Motor.

2. **MongoDB Indexes:**
   - Compound index on `(subject_id, topic)` for filtered question listing.
   - Index on `(user_id, status)` for staging queue queries.
   - `$text` index on `question_text` for search.

3. **Backend Route Splitting:**
   - `server.py` is currently monolithic (~1k LOC).
   - Split into `routes/` sub-modules per domain: `auth`, `questions`, `pyqs`, `analytics`, `drive`, `playlists`, `staging`.
   - Each module registers its own `APIRouter` and mounts via `app.include_router`.

4. **Mock Test Mode:**
   - Timed GATE-style simulation: 65 questions, 3 hours, negative marking (−1/3), auto-submit.
   - Questions sampled proportionally from subject-wise PYQ distribution.
   - Post-test report with section-wise accuracy and time-per-question.

---

## 🟢 Phase 10: PWA & Offline

1. **Service Worker:** Cache the PDF canvas reader assets offline.
2. **Offline Question Bank:** Cache last-loaded question set in IndexedDB for offline review.
3. **Manifest + icons:** Full PWA installable from browser.

---

## 💭 Exploratory Backlog
- AI conversational tutor (Chat with your notes via Gemini).
- Streak and Daily Goal HUD.
- Calibration diagnostic quiz on boarding.
- Multi-user collaborative question banks.
- Export question bank to Anki deck format.

---

<p align="center">
  <em>Last updated: June 2026.</em>
</p>
