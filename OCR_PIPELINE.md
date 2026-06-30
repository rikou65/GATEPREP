# PDF + OCR Ingestion Pipeline — Technical Reference

**Status:** Phase 5 core complete. Image extraction (Phase 5 continued) is the active next step.
**Last updated:** June 2026

---

## Overview

The OCR pipeline converts any GATE study material PDF into a structured, reviewable question bank using:
- **`mistral-ocr-latest`** — raw page-level markdown extraction
- **`mistral-large-latest`** — structured question/solution/concept parsing via `client.chat.parse`
- **`pypdfium2`** — PDF slicing before upload
- **MongoDB** — staging buffer before human approval

---

## Architecture

```
PDF file (upload)
    │
    ▼
[ pypdfium2: slice into 5-page chunks ]
    │
    ▼ (each chunk)
[ Mistral Files API: upload chunk ]
    │
    ▼
[ mistral-ocr-latest: page → markdown ]
    │
    ▼
[ mistral-large-latest: markdown → CombinedPassResponse ]
    │  (via client.chat.parse + Pydantic schema)
    │
    ├──► List[ExtractedQuestion]
    ├──► List[ExtractedSolution]
    └──► List[ExtractedConcept]
         │
         ▼
[ _stitch_and_save: normalize IDs → upsert staging_questions ]
         │
         ▼
[ Staging Queue UI: review → Approve / Discard ]
         │
         ▼
[ live questions / topic_concepts collections ]
```

---

## Pydantic Schemas

### `ExtractedQuestion`
| Field | Type | Description |
|---|---|---|
| `extracted_id` | `str` | Printed question ID verbatim (e.g. `Q.29`, `1`) |
| `question_text` | `str` | Verbatim question text. Math in `$...$`. Images as `![desc](img-N.jpeg)` |
| `options` | `List[str]` | Option texts only — no `(A)(B)` prefix. Math in `$...$`. Empty for NAT |
| `topic` | `str` | Section heading above question (e.g. `"Boolean Algebra"`) |
| `question_type` | `str` | `"MCQ"`, `"MSQ"`, or `"NAT"` |
| `is_pyq` | `bool` | True if tagged with a GATE year |
| `year` | `Optional[int]` | GATE year if `is_pyq` is true |
| `gate_set` | `Optional[str]` | e.g. `"Set 1"` |
| `gate_qnum` | `Optional[str]` | GATE question number if specified |

### `ExtractedSolution`
| Field | Type | Description |
|---|---|---|
| `target_id` | `str` | Question ID this solution belongs to |
| `correct_answer` | `str` | Answer letter(s) (`"A"`, `"A,C"`) or numeric value for NAT |
| `solution_text` | `str` | Verbatim step-by-step solution. Math in `$...$` |

### `ExtractedConcept`
| Field | Type | Description |
|---|---|---|
| `title` | `str` | Section heading |
| `content_markdown` | `str` | Theory, formulas, and notes in Markdown + KaTeX |

---

## ID Normalization

PDFs from sources like GO-PDFs label questions as `Q.1`–`Q.65` in the questions section and solutions as `1`–`65` in the answers section. Without normalization this produces 130 orphaned records instead of 65 complete ones.

```python
def normalize_id(raw_id: str) -> str:
    import re
    clean = re.sub(r'^[Qq][.\s]*', '', str(raw_id).strip())
    return clean.strip() or raw_id.strip()
```

**Examples:**
| Raw | Normalized |
|---|---|
| `Q.1` | `1` |
| `Q.29` | `29` |
| `Q1` | `1` |
| `1` | `1` |
| `1.1.4` | `1.1.4` (unchanged — no `Q.` prefix) |

`normalize_id()` is called before every DB lookup and insert in `_stitch_and_save`.

---

## Staging Status Flow

```
Question arrives first → ORPHANED_QUESTION
Solution arrives first → ORPHANED_SOLUTION
Both present          → READY
```

When a solution arrives for an existing `ORPHANED_QUESTION`, the record is updated in-place and status upgraded to `READY`. Same in reverse.

---

## Extraction Prompt (key rules enforced)

1. **VERBATIM EXTRACTION** — copy question/option/solution text exactly as printed. No rephrasing.
2. **ONE RECORD PER PRINTED QUESTION** — do not generate paraphrased rewrites.
3. **QUESTION ID** — capture exactly as printed. Link solutions by the same ID.
4. **MATH** — wrap all math in `$...$`. Convert bar notation to `\bar{X}`.
5. **TABLES** — render K-maps and truth tables as valid Markdown tables.
6. **IMAGES** — include `![description](img-N.jpeg)` at the position the image appears. Do not describe or skip.
7. **OPTIONS** — texts only, no `(A)(B)(C)(D)` prefixes.
8. **TOPIC** — from the nearest section heading above the question.
9. **QUESTION TYPE** — `MSQ` if tagged `[MSQ]`, `NAT` if no options, else `MCQ`.
10. **SOLUTIONS** — verbatim, linked by printed ID.

Temperature: `0.05` (near-deterministic to minimize hallucination).

---

## Chunk Size & Rate Limiting

- **Chunk size:** 5 pages per Mistral upload
- **Backoff sleep:** 5 seconds between chunks (avoids Mistral API rate limits)
- **Progress reporting:** `import_jobs.progress` updated after each chunk completes
- **Cleanup:** each uploaded Mistral file is deleted from Mistral's storage after OCR completes

---

## Backend API Routes

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/admin/import/pdf` | Upload PDF. Form params: `file`, `subject_id`, `engine` (`mistral`), `source` (optional). Kicks off background job. |
| `GET` | `/api/admin/import/jobs` | List last 10 import jobs for the current user. Returns `status`, `progress`, `total_pages`, `error`. |
| `DELETE` | `/api/admin/import/jobs/{job_id}` | Permanently delete a job record (dismiss from UI). |
| `GET` | `/api/admin/staging` | List all staging items sorted by `created_at` desc. |
| `DELETE` | `/api/admin/staging/{staging_id}` | Discard a single staging item. |
| `DELETE` | `/api/admin/staging` | Clear the entire staging queue. |
| `POST` | `/api/admin/staging/approve-specific` | Approve a single item by `staging_id` (force-approves orphans too). |
| `POST` | `/api/admin/staging/bulk-approve` | Approve all `READY` items in one shot. |

---

## Frontend Components

### `ImportPDF.jsx` (`/admin/import`)
- Subject selector (required).
- Source / Publisher text input (optional — user declares e.g. "GO-PDFs").
- Engine: Mistral AI only (LlamaAI option removed).
- On submit: `POST /api/admin/import/pdf` multipart form → redirects to staging queue.

### `StagingQueue.jsx` (`/admin/staging`)
- **Active jobs:** live progress bar per running job. Auto-refreshes every 5 seconds.
- **Failed jobs:** red error box per failed job with ✕ dismiss button → calls `DELETE /api/admin/import/jobs/{job_id}`.
- **Action Required section:** orphaned items with Force Approve / Discard.
- **Ready for DB section:** READY items with question text, math-rendered options, Approve / Discard.
- **Header bar:** item count stats, Approve All 100% Matches, Clear All.

### `mathFormat.jsx` (`src/lib/`)
Shared math rendering utility. Used in both `StagingQueue` and `QuestionViewer`.

| Input | Output |
|---|---|
| `$\bar{A}B + C$` | A̅B + C (rendered overline span) |
| `$\Sigma m(1,3,5)$` | Σm(1,3,5) |
| `$\oplus$` | ⊕ |
| `$\frac{a}{b}$` | a/b (inline fraction span) |
| `![Figure](img-4.jpeg)` | 📐 [Figure] placeholder chip |
| `$$...$$` | Display-block math span |

---

## Known Limitation — Images

Mistral's structured extraction pass (`client.chat.parse`) does **not** return base64 image data. It only produces markdown references like `![Figure Description](img-4.jpeg)`. These files do not exist on disk.

**Current behavior:** rendered as `📐 [Figure Description]` placeholder chip.

**Planned fix (Phase 5 continued):**
1. After `client.ocr.process()`, inspect `ocr_response.pages[n].images` — Mistral returns base64 here.
2. Store each image in a new `ocr_images` collection: `{ image_id, job_id, page_num, base64, mime_type }`.
3. Replace `img-N.jpeg` references in staging docs with `image_id` references.
4. Serve via `GET /api/admin/ocr-images/{image_id}`.
5. Update `mathFormat.jsx` to fetch and render as `<img>`.

---

## Environment Variables Required

| Variable | Where | Description |
|---|---|---|
| `MISTRAL_API_KEY` | `backend/.env` | Mistral AI API key. Read via `os.environ.get()` — **never** via `settings` object inside background tasks. |

---

## Running the Pipeline Manually (CLI)

```bash
cd backend
..\venv\Scripts\python scripts\mistral_ocr.py --pdf "path/to/file.pdf" --subject "<subject_id>"
```

This runs the full pipeline synchronously (no job tracking, no staging UI). Useful for debugging.
