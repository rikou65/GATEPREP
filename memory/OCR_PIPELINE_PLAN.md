# PDF + OCR Ingestion Pipeline (Phase 5)
## Technical Architecture & Execution Plan

**Goal:** Automate the ingestion of 5,000+ questions and key concepts from the highly-structured GO-PDFs repository into the GATE Study OS, minimizing manual intervention.

---

### Phase 1: The Python Orchestrator (`backend/scripts/import_go_pdfs.py`)
This is the master controller that prevents AI hallucination and manages Google API rate limits.

1. **PDF Slicer:** Uses `pypdfium2` to read the target PDF. It chunks the document into 5-10 page overlapping segments.
2. **Context Tracker:** Maintains a state machine to track the current Subject and Topic based on the Table of Contents or section headers.
3. **Rate Limiter:** Implements token-bucket rate limiting to stay within the free-tier Gemini API limits (e.g., 15 RPM). Implements exponential backoff on 429 errors.

---

### Phase 2: Dual-Pass Gemini Extraction
To solve the "Disconnected Context" problem (questions on page 10, answers on page 110), the script runs two distinct AI passes.

#### Pass A: "The Question Harvester"
- **Target:** Pages identified as containing practice problems.
- **Prompt Instruction:** "Extract questions to JSON. MUST capture the printed Question ID (e.g., '1.1.4'). Convert all math to standard KaTeX format."
- **Data Stored:** Staging DB `->` `{ temp_id: "1.1.4", text: "...", options: [...], solution: null, status: "AWAITING_SOLUTION" }`

#### Pass B: "The Solution Harvester"
- **Target:** Pages identified as the Answer Key / Solution blocks.
- **Prompt Instruction:** "Extract solutions. MUST capture the printed Question ID."
- **Data Extracted:** Memory Array `->` `[{ target_id: "1.1.4", answer: "A", solution_text: "..." }]`

#### The Concept Harvester (Parallel)
- Simultaneously, if the page is identified as "Theory", Gemini extracts the content into Markdown + KaTeX blocks and saves directly to the `topic_concepts` collection.

---

### Phase 3: The "Python Stitch" (Relational Merge)
1. **Deterministic Join:** The Python script queries the staging database and memory arrays, joining questions and solutions using the extracted `Question ID`.
2. **Fuzzy Fallback:** If IDs are missing, it uses text embedding similarity (TF-IDF) to match the first 10 words of the solution to a question.
3. **Validation:** Checks if the assembled JSON object has all required fields (`question_text`, `options`, `correct_answer`, `solution`).
4. **Confidence Scoring:**
   - Perfect ID Match = `100%` (Ready for bulk approve).
   - Fuzzy Match = `80%` (Requires quick visual check).
   - Orphaned = `0%` (Red flag in Review Queue).

---

### Phase 4: The Admin Staging Queue (Frontend UI)
A new screen at `/admin/staging`.

1. **Bulk Operations:** A prominent button: **"Approve all 100% Matches"**. This moves thousands of questions instantly into the live `db.questions` or `db.pyqs` collections.
2. **Triage View:** A filtered list of "Orphans" or low-confidence matches.
3. **Inline Edit:** A quick form to paste a missing solution or fix a broken LaTeX tag before clicking "Approve."

---

### Execution Steps (Starting Now)

1. **Step 1 (Backend):** Create the `topic_concepts` and `staging_questions` MongoDB collections and their FastAPI routes.
2. **Step 2 (Backend):** Write the `import_go_pdfs.py` script. Integrate `google-genai` (Gemini SDK) and configure the Structured Output JSON schemas.
3. **Step 3 (Backend):** Implement the "Stitching" logic and Rate Limiter.
4. **Step 4 (Frontend):** Build the `/admin/staging` Review Queue UI with the "Bulk Approve" feature.
