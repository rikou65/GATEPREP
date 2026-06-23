"""
Phase 5 Hybrid: LlamaParse Text + PyMuPDF Image Ripper
Uses LlamaParse to grab perfect text/math and PyMuPDF to extract embedded diagrams.
"""

import os
import re
import sys
import asyncio
import nest_asyncio
import argparse
import fitz  # PyMuPDF
from llama_parse import LlamaParse
from pydantic import BaseModel

nest_asyncio.apply()

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared import db, new_id, now_utc, iso, logger

FRONTEND_PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/public/unacademy_images"))
os.makedirs(FRONTEND_PUBLIC_DIR, exist_ok=True)

async def parse_with_llama(pdf_path: str, subject_id: str, job_id: str = None):
    logger.info(f"Starting LlamaParse + Image Ripper for {pdf_path}")
    
    if job_id:
        await db.import_jobs.update_one({"job_id": job_id}, {"$set": {"status": "PROCESSING", "progress": 10, "total_pages": 100}})

    # 1. Native Image Ripping using PyMuPDF
    doc = fitz.open(pdf_path)
    all_extracted_images = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            try:
                base_image = doc.extract_image(img[0])
                img_name = f"llama_{job_id or 'local'}_p{page_num+1}_i{img_index}.{base_image['ext']}"
                img_path = os.path.join(FRONTEND_PUBLIC_DIR, img_name)
                with open(img_path, "wb") as f:
                    f.write(base_image["image"])
                all_extracted_images.append(img_name)
            except Exception as e:
                logger.error(f"Failed to extract image on page {page_num+1}: {e}")
    doc.close()
    logger.info(f"Successfully ripped {len(all_extracted_images)} images.")

    if job_id:
        await db.import_jobs.update_one({"job_id": job_id}, {"$set": {"progress": 30}})

    # 2. Text Extraction using LlamaParse
    logger.info("Sending to LlamaParse API...")
    parser = LlamaParse(
        result_type="markdown",
        verbose=True,
        language="en",
        num_workers=4,
    )
    
    # Offload LlamaParse network call to thread
    parsed_docs = await asyncio.to_thread(parser.load_data, pdf_path)
    full_markdown = "\n".join([d.text for d in parsed_docs])
    
    if job_id:
        await db.import_jobs.update_one({"job_id": job_id}, {"$set": {"progress": 80}})

    # 3. Use Gemini to structure the clean Markdown into JSON (Lightning fast, no image rate limits)
    logger.info("Structuring Markdown with Gemini...")
    from google import genai
    from google.genai import types
    from scripts.import_go_pdfs import QuestionPassResponse, SolutionPassResponse
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    You are a data extraction assistant. I have already converted a GATE workbook PDF into Markdown.
    Extract all the actual practice questions and solutions from this markdown into structured JSON.
    
    RULES:
    1. Ignore raw answer keys (e.g., '1. A 2. B') unless you can map them to the correct question. Do not create blank questions just for answer keys.
    2. MUST capture the printed Question ID (e.g., '1.1.4', 'Q12') as extracted_id.
    3. Separate the main question text from multiple-choice options.
    4. Keep math in KaTeX format ($...$).
    
    MARKDOWN CONTENT:
    {full_markdown[:30000]} # Limit to 30k chars to stay safe
    """
    
    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QuestionPassResponse,
            temperature=0.1,
        ),
    )
    
    questions = response.parsed.questions if response.parsed else []
    
    sol_prompt = f"""
    Extract the solutions from this markdown. Match them to the target_id.
    MARKDOWN CONTENT:
    {full_markdown[:30000]}
    """
    sol_response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=sol_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SolutionPassResponse,
            temperature=0.1,
        ),
    )
    solutions = sol_response.parsed.solutions if sol_response.parsed else []

    # 4. Inject Image Links
    if questions and all_extracted_images:
        img_markdown = "\n\n**Extracted Diagrams:**\n" + "\n".join([f"![Diagram](/unacademy_images/{img})" for img in all_extracted_images])
        questions[0].question_text += img_markdown

    # 5. Save to Staging
    db_docs = []
    sol_map = {s.target_id: s for s in solutions}
    
    for q in questions:
        sol = sol_map.get(q.extracted_id)
        db_docs.append({
            "staging_id": new_id("stg"),
            "subject_id": subject_id,
            "extracted_id": q.extracted_id,
            "question_text": q.question_text,
            "options": q.options,
            "is_pyq": q.is_pyq,
            "year": q.year,
            "gate_set": q.gate_set,
            "gate_qnum": q.gate_qnum,
            "correct_answer": sol.correct_answer if sol else None,
            "solution_text": sol.solution_text if sol else None,
            "status": "READY" if sol else "ORPHANED_QUESTION",
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc())
        })
        
    if db_docs:
        await db.staging_questions.insert_many(db_docs)
        logger.info(f"Successfully inserted {len(db_docs)} items into Staging Queue via LlamaParse+Gemini.")
        
    if job_id:
        await db.import_jobs.update_one({"job_id": job_id}, {"$set": {"status": "COMPLETED", "progress": 100, "completed_at": iso(now_utc())}})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF file")
    parser.add_argument("--subject", type=str, required=True, help="Subject ID")
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(parse_with_llama(args.pdf, args.subject))
