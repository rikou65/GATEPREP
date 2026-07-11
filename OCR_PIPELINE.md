# GATEPREP — OCR and Staging Pipeline

This document explains the current OCR ingestion flow so contributors can work
on it without reverse-engineering the pipeline from code.

## Purpose

The OCR pipeline converts uploaded GATE study PDFs into structured staging
documents that a user can review and approve into the live question bank.

## AI Used

The OCR pipeline is AI-powered and is not a manual process.

Current provider and usage:

- **Mistral OCR** for raw OCR extraction from uploaded PDF pages
- **Mistral structured parsing** for converting extracted content into question,
  solution, and concept records

In practice, the pipeline uses Mistral for:

- OCR of PDF page content
- extraction of structured question data
- extraction of solutions
- extraction of topic/concept content for staging

## Current Flow

1. User opens the Import PDF page
2. User selects a subject and optional source/publisher
3. Frontend sends a multipart upload to `/api/data/import/pdf`
4. Backend starts an OCR import job
5. OCR output is stitched into staging collections
6. User reviews items in the staging queue
7. User approves, force-approves, discards, or clears staging items

## Current Routes

All OCR and staging routes are under `/api/data/*`.

- `POST /api/data/import/pdf`
- `GET /api/data/import/jobs`
- `DELETE /api/data/import/jobs/{job_id}`
- `GET /api/data/staging`
- `DELETE /api/data/staging/{staging_id}`
- `DELETE /api/data/staging`
- `POST /api/data/staging/approve-specific`
- `POST /api/data/staging/bulk-approve`

Legacy `/api/admin/*` references are retired and should not be reintroduced.

## Core Data Objects

### `import_jobs`

Tracks an OCR job from upload through completion/failure.

Important fields:

- `job_id`
- `user_id`
- `filename`
- `engine`
- `source`
- `status`
- `progress`
- `total_pages`
- `error`

### `staging_questions`

Stores OCR-extracted items pending review.

Important fields:

- `staging_id`
- `user_id`
- `subject_id`
- `topic`
- `source`
- `question_text`
- `options`
- `question_type`
- `correct_answer`
- `solution_text`
- `status`

### `topic_concepts`

Stores extracted concept/theory blocks associated with OCR imports.

## Status Model

- `READY` — question and solution are both present
- `ORPHANED_QUESTION` — question exists without solution
- `ORPHANED_SOLUTION` — solution exists without question

## Extraction Behavior

The OCR flow is designed around:

- page-level OCR extraction
- structured parsing into typed question/solution/concept records
- normalization and merge of split question/solution sections

The current OCR implementation depends on AI extraction rather than manual
templated parsing, because the imported PDFs vary in structure, formatting,
math notation, and layout.

Important behavioral requirements:

- question and solution text should be preserved as faithfully as possible
- source is user-supplied at upload time, not hardcoded
- no `difficulty` metadata should be injected
- topic should come from surrounding document structure where possible

## Known Active Limitations

- OCR image extraction is not yet production-complete
- staging and OCR flows are now tenant-isolated (Phase 2 completed)
- queue durability and production worker architecture are planned later in the roadmap

## Relationship To The Roadmap

The OCR pipeline is governed by:

- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for phase ordering
- [ARCHITECTURE.md](./ARCHITECTURE.md) for system boundaries

If OCR behavior changes, update this file and the roadmap together.
