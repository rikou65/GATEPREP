"""
Phase 5: GO-PDF Ingestion Pipeline (OCR + Gemini 1.5 Flash)
This script orchestrates the dual-pass extraction of Questions and Concepts from GO-PDFs.
"""

import os
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

import pypdfium2 as pdfium
import fitz
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Ensure we can import from the parent backend directory
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared import db, new_id, now_utc, iso, logger, settings

FRONTEND_PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/public/unacademy_images"))
os.makedirs(FRONTEND_PUBLIC_DIR, exist_ok=True)

# =====================================================================
# 1. Pydantic Schemas for Gemini Structured Output
# =====================================================================

class ExtractedQuestion(BaseModel):
    extracted_id: str = Field(description="The printed Question ID or number (e.g., '1.1.4', 'Q12'). MUST be captured.")
    question_text: str = Field(description="The full text of the question, using KaTeX for math formulas.")
    options: List[str] = Field(description="List of options if MCQ or MSQ. Empty list if NAT.")
    is_pyq: bool = Field(description="True if the question is tagged with a GATE year.")
    year: Optional[int] = Field(description="The GATE year if is_pyq is true.")
    gate_set: Optional[str] = Field(description="The GATE paper set if specified, e.g., 'Set 1' or 'Set 2'. Null if not specified.")
    gate_qnum: Optional[str] = Field(description="The actual GATE question number if specified, e.g., '34' or 'Q34'. Null if not specified.")

class ExtractedSolution(BaseModel):
    target_id: str = Field(description="The Question ID this solution belongs to (e.g., '1.1.4').")
    correct_answer: str = Field(description="The final correct answer or option key.")
    solution_text: str = Field(description="The step-by-step solution, using KaTeX for math.")

class ExtractedConcept(BaseModel):
    title: str = Field(description="The heading or title of this concept block.")
    content_markdown: str = Field(description="The theory, notes, or formulas in Markdown + KaTeX format.")

class QuestionPassResponse(BaseModel):
    questions: List[ExtractedQuestion]

class SolutionPassResponse(BaseModel):
    solutions: List[ExtractedSolution]

class ConceptPassResponse(BaseModel):
    concepts: List[ExtractedConcept]

# =====================================================================
# 2. Pipeline Orchestrator
# =====================================================================

class PDFOrchestrator:
    def __init__(self, pdf_path: str, subject_id: str, job_id: Optional[str] = None):
        self.pdf_path = pdf_path
        self.subject_id = subject_id
        self.job_id = job_id
        
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is missing from .env")
            
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash" 

    def _slice_pdf(self, start_page: int, end_page: int) -> str:
        """Extract a specific range of pages into a new PDF in-memory."""
        pdf = pdfium.PdfDocument(self.pdf_path)
        new_pdf = pdfium.PdfDocument.new()
        actual_end = min(end_page, len(pdf))
        new_pdf.import_pages(pdf, list(range(start_page, actual_end)))
        temp_path = f"temp_chunk_{start_page}_{actual_end}.pdf"
        new_pdf.save(temp_path)
        new_pdf.close()
        pdf.close()
        return temp_path

    async def _upload_to_gemini(self, file_path: str, mime_type: str = "application/pdf"):
        """Upload a file to Gemini's File API for processing using a thread pool."""
        logger.info(f"Uploading chunk {file_path} to Gemini...")
        
        # Offload synchronous upload to a thread
        gemini_file = await asyncio.to_thread(
            self.client.files.upload, file=file_path, config={"mime_type": mime_type}
        )
        
        while gemini_file.state == "PROCESSING":
            logger.info("Waiting for file processing...")
            await asyncio.sleep(2)
            gemini_file = await asyncio.to_thread(self.client.files.get, name=gemini_file.name)
            
        if gemini_file.state == "FAILED":
            raise RuntimeError("Gemini failed to process the PDF chunk.")
        return gemini_file

    async def _safe_generate_content(self, contents: list, schema: Any, prompt: str):
        """Wrapper to handle retries on 429 errors with exponential backoff."""
        max_retries = 5
        base_delay = 30 # Start with 30s wait on 429
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=contents + [prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.1,
                    ),
                )
                return response.parsed
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit. Waiting {wait_time}s (Attempt {attempt+1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
        raise RuntimeError("Max retries exceeded for Gemini API.")

    async def extract_questions(self, gemini_file) -> List[ExtractedQuestion]:
        """Pass A: Harvest Questions (Non-blocking)"""
        prompt = (
            "You are a strict data extraction assistant. Extract all practice questions from this document into structured JSON. "
            "RULES: "
            "1. MUST capture the printed Question ID (e.g., '1.1.4'). "
            "2. Separate the main question text from its multiple-choice options. Put options ONLY in the 'options' array. "
            "3. If options are present (MCQ/MSQ), extract them cleanly without letters like '(A)' or '(B)'. Just the value. "
            "4. Format all math using standard KaTeX ($...$). "
            "5. Remove extraneous symbols or formatting artifacts. "
            "6. If the question has a GATE year tag (e.g. GATE 2021 Set 1 Q34), set is_pyq=true, extract the year, gate_set ('Set 1'), and gate_qnum ('34'). "
            "If there are no questions, return an empty array."
        )
        parsed = await self._safe_generate_content([gemini_file], QuestionPassResponse, prompt)
        if not parsed or not hasattr(parsed, 'questions'):
            return []
        return parsed.questions

    async def extract_solutions(self, gemini_file) -> List[ExtractedSolution]:
        """Pass B: Harvest Solutions (Non-blocking)"""
        prompt = (
            "You are a strict data extraction assistant. Extract all answer keys and detailed solutions from this document. "
            "RULES: "
            "1. MUST capture the exact printed Question ID (e.g., '1.1.4') as 'target_id'. "
            "2. 'correct_answer' must be the final, exact answer (e.g., 'A', '10.5'). Do not include the whole solution here. "
            "3. 'solution_text' must contain the full, step-by-step explanation. "
            "4. Format all math using standard KaTeX ($...$). Remove messy symbols. "
            "If the page has NO solutions, return an empty array."
        )
        parsed = await self._safe_generate_content([gemini_file], SolutionPassResponse, prompt)
        if not parsed or not hasattr(parsed, 'solutions'):
            return []
        return parsed.solutions

    async def extract_concepts(self, gemini_file) -> List[ExtractedConcept]:
        """Pass C: Harvest Theory and Notes (Non-blocking)"""
        prompt = (
            "You are a GATE CSE expert. Extract all theory, study notes, key concepts, and formulas from this document. "
            "Do NOT extract practice questions or solutions here. "
            "Format the content using clean Markdown and standard KaTeX ($...$) for math. "
            "If the page has NO theory or notes, return an empty array."
        )
        parsed = await self._safe_generate_content([gemini_file], ConceptPassResponse, prompt)
        if not parsed or not hasattr(parsed, 'concepts'):
            return []
        return parsed.concepts

    async def process_pdf(self):
        """Main loop to slice, extract, and save to DB."""
        pdf = pdfium.PdfDocument(self.pdf_path)
        total_pages = len(pdf)
        chunk_size = 5 # 5 pages at a time to stay well within output limits

        logger.info(f"Starting OCR pipeline for {self.pdf_path} ({total_pages} pages)")
        
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
                    gemini_file = await self._upload_to_gemini(temp_file)
                    
                    logger.info(f"Processing pages {start_page+1} to {end_page}...")
                    
                    concepts = await self.extract_concepts(gemini_file)
                    questions = await self.extract_questions(gemini_file)
                    solutions = await self.extract_solutions(gemini_file)
                    
                    logger.info(f"  Found: {len(concepts)} concepts, {len(questions)} questions, {len(solutions)} solutions.")
                    
                    # Incrementally save and stitch to DB so UI updates in real-time
                    await self._stitch_and_save(questions, solutions, concepts)
                    
                    # Update progress
                    if self.job_id:
                        await db.import_jobs.update_one(
                            {"job_id": self.job_id},
                            {"$set": {"progress": end_page}}
                        )
                    
                    # Cleanup remote file
                    await asyncio.to_thread(self.client.files.delete, name=gemini_file.name)
                    
                    # Sleep to respect rate limits - USE ASYNC SLEEP
                    await asyncio.sleep(10) 
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {start_page}-{end_page}: {e}")
                finally:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except Exception as e:
                            logger.error(f"Failed to remove temp chunk {temp_file}: {e}")

            logger.info("OCR Pipeline completed successfully.")
            if self.job_id:
                await db.import_jobs.update_one({"job_id": self.job_id}, {"$set": {"status": "COMPLETED", "progress": total_pages, "completed_at": iso(now_utc())}})
        finally:
            pdf.close()

    async def _stitch_and_save(self, questions: List[ExtractedQuestion], solutions: List[ExtractedSolution], concepts: List[ExtractedConcept]):
        """Incremental relational merge and upsert into staging database."""
        
        if concepts:
            logger.info(f"Saving {len(concepts)} concepts to database...")
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
                existing = await db.staging_questions.find_one({"subject_id": self.subject_id, "extracted_id": q.extracted_id})
                if existing:
                    # Update if we find a solution
                    status = "READY" if (existing.get("correct_answer") or existing.get("solution_text")) else "ORPHANED_QUESTION"
                    await db.staging_questions.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "question_text": q.question_text,
                            "options": q.options,
                            "is_pyq": q.is_pyq,
                            "year": q.year,
                            "gate_set": q.gate_set,
                            "gate_qnum": q.gate_qnum,
                            "status": status,
                            "updated_at": iso(now_utc())
                        }}
                    )
                else:
                    doc = {
                        "staging_id": new_id("stg"),
                        "subject_id": self.subject_id,
                        "extracted_id": q.extracted_id,
                        "question_text": q.question_text,
                        "options": q.options,
                        "is_pyq": q.is_pyq,
                        "year": q.year,
                        "gate_set": q.gate_set,
                        "gate_qnum": q.gate_qnum,
                        "correct_answer": None,
                        "solution_text": None,
                        "status": "ORPHANED_QUESTION",
                        "created_at": iso(now_utc()),
                        "updated_at": iso(now_utc())
                    }
                    await db.staging_questions.insert_one(doc)
                    
        if solutions:
            for sol in solutions:
                existing = await db.staging_questions.find_one({"subject_id": self.subject_id, "extracted_id": sol.target_id})
                if existing:
                    status = "READY" if existing.get("question_text") else "ORPHANED_SOLUTION"
                    await db.staging_questions.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "correct_answer": sol.correct_answer,
                            "solution_text": sol.solution_text,
                            "status": status,
                            "updated_at": iso(now_utc())
                        }}
                    )
                else:
                    doc = {
                        "staging_id": new_id("stg"),
                        "subject_id": self.subject_id,
                        "extracted_id": sol.target_id,
                        "question_text": None,
                        "options": [],
                        "is_pyq": False,
                        "year": None,
                        "gate_set": None,
                        "gate_qnum": None,
                        "correct_answer": sol.correct_answer,
                        "solution_text": sol.solution_text,
                        "status": "ORPHANED_SOLUTION",
                        "created_at": iso(now_utc()),
                        "updated_at": iso(now_utc())
                    }
                    await db.staging_questions.insert_one(doc)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run GO-PDF OCR Pipeline")
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF file")
    parser.add_argument("--subject", type=str, required=True, help="Subject ID to map these imports to")
    
    args = parser.parse_args()
    
    async def main():
        orchestrator = PDFOrchestrator(args.pdf, args.subject)
        await orchestrator.process_pdf()
        
    asyncio.run(main())
