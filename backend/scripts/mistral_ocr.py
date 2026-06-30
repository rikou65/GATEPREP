"""
Mistral AI OCR Ingestion Pipeline (OCR + Mistral Large)
Orchestrates page slicing, Mistral OCR, structured chat parsing, and relational stitching.
"""

import os
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

import pypdfium2 as pdfium
from mistralai.client import Mistral
from pydantic import BaseModel, Field

# Ensure we can import from parent directory
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared import db, new_id, now_utc, iso, logger

# Read API key directly from env to avoid 'settings' scope issues
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# =====================================================================
# 1. Pydantic Schemas for Mistral Structured Output
# =====================================================================

class ExtractedQuestion(BaseModel):
    extracted_id: str = Field(description="The printed Question ID or number exactly as it appears (e.g., 'Q.1', 'Q.29', '1'). MUST be captured verbatim.")
    question_text: str = Field(
        description=(
            "Copy the question text EXACTLY as printed. Do NOT rephrase, rewrite, or add extra words. "
            "Wrap all math/equations in standard LaTeX/KaTeX ($...$). "
            "Convert Boolean bar notation (X̅, X with bar) to \\bar{X} or \\overline{X}. "
            "If the question references a figure or image, write: ![Figure Description](img-N.jpeg) in the text where the image appears."
        )
    )
    options: List[str] = Field(
        description=(
            "List of option texts EXACTLY as printed. Remove leading labels like (A), (B), A., B. from each option value. "
            "Empty list if NAT or no options. Wrap math in $...$."
        )
    )
    topic: str = Field(
        description=(
            "The section/topic this question belongs to, inferred from the nearest section heading above it. "
            "Examples: 'Number System', 'Boolean Algebra', 'Logic Gates', 'Combinational Circuits', 'Sequential Circuit'. "
            "Use the exact heading text from the document."
        )
    )
    question_type: str = Field(
        description="'MCQ' if exactly one answer, 'MSQ' if multiple answers possible (marked [MSQ]), 'NAT' if numerical answer. Default 'MCQ'."
    )
    is_pyq: bool = Field(description="True if the question is tagged with a GATE year.")
    year: Optional[int] = Field(description="The GATE year if is_pyq is true.", default=None)
    gate_set: Optional[str] = Field(description="The GATE paper set if specified, e.g., 'Set 1'. Null if not specified.", default=None)
    gate_qnum: Optional[str] = Field(description="The GATE question number if specified. Null if not specified.", default=None)

class ExtractedSolution(BaseModel):
    target_id: str = Field(description="The Question ID this solution belongs to (e.g., 'Q.1', '1').")
    correct_answer: str = Field(description="The final correct answer letter (A, B, C, D) or value for NAT. For MSQ, comma-separated letters.")
    solution_text: str = Field(
        description=(
            "Copy the step-by-step solution text EXACTLY as printed. Do NOT rephrase or summarize. "
            "Wrap all math in $...$. Convert bar notation to \\bar{X}."
        )
    )

class ExtractedConcept(BaseModel):
    title: str = Field(description="The heading or title of this concept block.")
    content_markdown: str = Field(description="The theory, notes, or formulas in Markdown + KaTeX format.")

class CombinedPassResponse(BaseModel):
    questions: List[ExtractedQuestion] = Field(default_factory=list)
    solutions: List[ExtractedSolution] = Field(default_factory=list)
    concepts: List[ExtractedConcept] = Field(default_factory=list)

# =====================================================================
# 2. Pipeline Orchestrator
# =====================================================================

class MistralOCRPipeline:
    def __init__(self, pdf_path: str, subject_id: str, job_id: Optional[str] = None, source: str = ""):
        self.pdf_path = pdf_path
        self.subject_id = subject_id
        self.job_id = job_id
        self.source = source
        
        api_key = MISTRAL_API_KEY
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is missing from environment / .env")
            
        self.client = Mistral(api_key=api_key)
        self.ocr_model = "mistral-ocr-latest"
        self.chat_model = "mistral-large-latest"

    def _slice_pdf(self, start_page: int, end_page: int) -> str:
        """Extract a specific range of pages into a new PDF on disk."""
        pdf = pdfium.PdfDocument(self.pdf_path)
        new_pdf = pdfium.PdfDocument.new()
        actual_end = min(end_page, len(pdf))
        new_pdf.import_pages(pdf, list(range(start_page, actual_end)))
        temp_path = f"temp_mistral_{start_page}_{actual_end}.pdf"
        new_pdf.save(temp_path)
        new_pdf.close()
        pdf.close()
        return temp_path

    async def _upload_to_mistral(self, file_path: str) -> Any:
        """Upload chunk to Mistral Files API."""
        logger.info(f"Uploading chunk {file_path} to Mistral...")
        
        with open(file_path, "rb") as f:
            uploaded_file = await asyncio.to_thread(
                self.client.files.upload,
                file={
                    "file_name": os.path.basename(file_path),
                    "content": f,
                },
                purpose="ocr"
            )
        return uploaded_file

    async def _extract_content(self, markdown_text: str) -> CombinedPassResponse:
        """Parse raw OCR markdown into structured model data using Mistral chat parse."""
        prompt = (
            "You are a STRICT VERBATIM data extraction assistant. Your job is to extract questions, "
            "solutions, and concept/theory blocks from this OCR Markdown of a GATE CS study material PDF.\n\n"
            "CRITICAL RULES — violating these is a failure:\n"
            "1. VERBATIM EXTRACTION: Copy question text and option text EXACTLY as printed. "
            "   Do NOT rewrite, rephrase, summarize, or add words. If the question says "
            "   'What is the gray code word for the binary number 101011?' then extract EXACTLY that.\n"
            "2. ONE RECORD PER PRINTED QUESTION: Only extract questions that actually appear printed in the PDF. "
            "   Do NOT generate paraphrased or instruction-style rewrites of questions.\n"
            "3. QUESTION ID: Capture the printed number exactly (e.g. 'Q.1', 'Q.29', '1', '1.1'). "
            "   Use this ID to link questions and solutions.\n"
            "4. MATH: Wrap all math/formulas in $...$. Convert complement/bar notation to \\bar{X}.\n"
            "5. TABLES: Render K-maps and truth tables as valid Markdown tables with matching column counts in ALL rows.\n"
            "6. IMAGES: If a question references a circuit diagram or figure, include ![description](img-N.jpeg) "
            "   in the question text at the position where the image appears. Do not describe or omit it.\n"
            "7. OPTIONS: Extract option texts only, without the (A)(B)(C)(D) prefixes. Wrap math in $...$.\n"
            "8. TOPIC: Identify which section heading (e.g. 'Number System', 'Boolean Algebra', 'Logic Gates', "
            "   'Combinational Circuits', 'Sequential Circuit') the question falls under.\n"
            "9. QUESTION TYPE: Mark as MSQ if the question has [MSQ] tag, NAT if it's a fill-in-the-blank "
            "   with no options, else MCQ.\n"
            "10. SOLUTIONS: Extract solution text verbatim, link to the question by its printed ID.\n"
            "11. QUESTIONS VS SOLUTIONS SEPARATION: The document has distinct 'Practice Questions' and 'Explanations' sections. "
            "    NEVER extract text from the 'Explanations' section into the 'questions' array. "
            "    If an item starts with numbers like '1. (D)' or is under 'Explanations', extract it ONLY as a solution.\n"
        )
        
        response = await asyncio.to_thread(
            self.client.chat.parse,
            model=self.chat_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": markdown_text}
            ],
            response_format=CombinedPassResponse,
            temperature=0.05
        )
        return response.choices[0].message.parsed

    async def process_pdf(self):
        """Main loop to slice, OCR, parse, and save to DB."""
        pdf = pdfium.PdfDocument(self.pdf_path)
        total_pages = len(pdf)
        chunk_size = 5  # Process 5 pages at a time

        logger.info(f"Starting Mistral OCR pipeline for {self.pdf_path} ({total_pages} pages)")
        
        if self.job_id:
            await db.import_jobs.update_one(
                {"job_id": self.job_id},
                {"$set": {"total_pages": total_pages, "progress": 0}}
            )

        try:
            for start_page in range(0, total_pages, chunk_size):
                end_page = min(start_page + chunk_size, total_pages)
                temp_file = self._slice_pdf(start_page, end_page)
                
                try:
                    uploaded_file = await self._upload_to_mistral(temp_file)
                    
                    logger.info(f"Processing Mistral OCR for pages {start_page+1} to {end_page}...")
                    
                    ocr_response = await asyncio.to_thread(
                        self.client.ocr.process,
                        model=self.ocr_model,
                        document={"file_id": uploaded_file.id}
                    )
                    
                    # Concat markdown from all pages in the chunk
                    chunk_markdown = "\n\n".join([page.markdown for page in ocr_response.pages])
                    
                    # Parse into structured Pydantic response
                    extracted = await self._extract_content(chunk_markdown)
                    
                    questions = extracted.questions or []
                    solutions = extracted.solutions or []
                    concepts = extracted.concepts or []
                    
                    logger.info(f"  Found: {len(concepts)} concepts, {len(questions)} questions, {len(solutions)} solutions.")
                    
                    # Stitch and save
                    await self._stitch_and_save(questions, solutions, concepts)
                    
                    # Update progress
                    if self.job_id:
                        await db.import_jobs.update_one(
                            {"job_id": self.job_id},
                            {"$set": {"progress": end_page}}
                        )
                        
                    # Cleanup Mistral file storage
                    try:
                        await asyncio.to_thread(self.client.files.delete, name=uploaded_file.id)
                    except Exception:
                        pass
                    
                    # Backoff sleep
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {start_page}-{end_page}: {e}")
                finally:
                    if os.path.exists(temp_file):
                        try: os.remove(temp_file)
                        except: pass

            logger.info("Mistral OCR Pipeline completed successfully.")
            if self.job_id:
                await db.import_jobs.update_one(
                    {"job_id": self.job_id},
                    {"$set": {"status": "COMPLETED", "progress": total_pages, "completed_at": iso(now_utc())}}
                )
        finally:
            pdf.close()

    async def _stitch_and_save(self, questions: List[ExtractedQuestion], solutions: List[ExtractedSolution], concepts: List[ExtractedConcept]):
        """Incremental relational merge and upsert into staging database."""

        def normalize_id(raw_id: str) -> str:
            """Normalize Q.1, Q1, q.1, 1 → '1'; Q.29 → '29'; keeps alphanumeric only."""
            import re
            # Strip leading Q/q and dots/spaces, keep the number/alphanum part
            clean = re.sub(r'^[Qq][.\s]*', '', str(raw_id).strip())
            return clean.strip() or raw_id.strip()

        if concepts:
            for c in concepts:
                doc = {
                    "concept_id": new_id("con"),
                    "subject_id": self.subject_id,
                    "title": c.title,
                    "content_markdown": c.content_markdown,
                    "created_at": iso(now_utc())
                }
                await db.topic_concepts.insert_one(doc)
            
        if questions:
            for q in questions:
                norm_id = normalize_id(q.extracted_id)
                existing = await db.staging_questions.find_one({"subject_id": self.subject_id, "extracted_id": norm_id})
                if existing:
                    status = "READY" if (existing.get("correct_answer") or existing.get("solution_text")) else "ORPHANED_QUESTION"
                    
                    # PROTECT EXISTING QUESTIONS: If the database already has question_text, 
                    # do not overwrite it. This prevents hallucinated questions from the 
                    # solutions section from overwriting the real question text.
                    update_data = {
                        "status": status,
                        "updated_at": iso(now_utc())
                    }
                    
                    if not existing.get("question_text") or len(existing.get("question_text", "")) < 10:
                        update_data.update({
                            "question_text": q.question_text,
                            "options": q.options,
                            "topic": q.topic,
                            "question_type": q.question_type,
                            "is_pyq": q.is_pyq,
                            "year": q.year,
                            "gate_set": q.gate_set,
                            "gate_qnum": q.gate_qnum,
                        })

                    await db.staging_questions.update_one(
                        {"_id": existing["_id"]},
                        {"$set": update_data}
                    )
                else:
                    doc = {
                        "staging_id": new_id("stg"),
                        "subject_id": self.subject_id,
                        "extracted_id": norm_id,
                        "question_text": q.question_text,
                        "options": q.options,
                        "topic": q.topic,
                        "question_type": q.question_type,
                        "is_pyq": q.is_pyq,
                        "year": q.year,
                        "gate_set": q.gate_set,
                        "gate_qnum": q.gate_qnum,
                        "correct_answer": None,
                        "solution_text": None,
                        "source": self.source,
                        "status": "ORPHANED_QUESTION",
                        "created_at": iso(now_utc()),
                        "updated_at": iso(now_utc())
                    }
                    await db.staging_questions.insert_one(doc)
                    
        if solutions:
            for sol in solutions:
                norm_id = normalize_id(sol.target_id)
                existing = await db.staging_questions.find_one({"subject_id": self.subject_id, "extracted_id": norm_id})
                if existing:
                    status = "READY" if existing.get("question_text") else "ORPHANED_SOLUTION"
                    ans_map = {"A": "0", "B": "1", "C": "2", "D": "3", "a": "0", "b": "1", "c": "2", "d": "3"}
                    mapped_ans = ans_map.get(sol.correct_answer.strip(), sol.correct_answer.strip()) if sol.correct_answer else None
                    if existing.get("question_type") == "MSQ" and sol.correct_answer:
                        parts = [p.strip() for p in sol.correct_answer.split(",")]
                        mapped_ans = [ans_map.get(p, p) for p in parts]

                    await db.staging_questions.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "correct_answer": mapped_ans,
                            "solution_text": sol.solution_text,
                            "status": status,
                            "updated_at": iso(now_utc())
                        }}
                    )
                else:
                    doc = {
                        "staging_id": new_id("stg"),
                        "subject_id": self.subject_id,
                        "extracted_id": norm_id,
                        "question_text": None,
                        "options": [],
                        "topic": "",
                        "question_type": "MCQ",
                        "is_pyq": False,
                        "year": None,
                        "gate_set": None,
                        "gate_qnum": None,
                        "correct_answer": sol.correct_answer,
                        "solution_text": sol.solution_text,
                        "source": self.source,
                        "status": "ORPHANED_SOLUTION",
                        "created_at": iso(now_utc()),
                        "updated_at": iso(now_utc())
                    }
                    await db.staging_questions.insert_one(doc)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Mistral OCR Pipeline")
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF file")
    parser.add_argument("--subject", type=str, required=True, help="Subject ID to map these imports to")
    
    args = parser.parse_args()
    
    async def main():
        pipeline = MistralOCRPipeline(args.pdf, args.subject)
        await pipeline.process_pdf()
        
    asyncio.run(main())
