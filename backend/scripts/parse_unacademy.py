"""
Local PyMuPDF Parser for Unacademy Digital PDFs.
Extracts questions, options, solutions, and directly rips embedded images to the frontend.
"""

import os
import re
import sys
import asyncio
import argparse
import fitz  # PyMuPDF

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared import db, new_id, now_utc, iso, logger

# The folder where the React frontend expects public images
FRONTEND_PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/public/unacademy_images"))
os.makedirs(FRONTEND_PUBLIC_DIR, exist_ok=True)

async def parse_unacademy_pdf(pdf_path: str):
    logger.info(f"Opening {pdf_path} with PyMuPDF...")
    doc = fitz.open(pdf_path)
    
    # Try to find the TOC subject, fallback to first subject found
    subject = await db.subjects.find_one({"name": {"$regex": "Theory of Computation", "$options": "i"}})
    if not subject:
        subject = await db.subjects.find_one()
    subject_id = subject["subject_id"] if subject else "sub_fallback"
    
    questions = []
    current_q = None
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Extract Images on this page directly to disk
        image_list = page.get_images(full=True)
        page_images = []
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                img_name = f"p{page_num+1}_img{img_index}.{image_ext}"
                img_path = os.path.join(FRONTEND_PUBLIC_DIR, img_name)
                
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                page_images.append(img_name)
                logger.info(f"Extracted Image: {img_name}")
            except Exception as e:
                logger.error(f"Failed to extract image on page {page_num+1}: {e}")
        
        # 2. Extract Text Blocks (ordered by vertical position Y)
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: b[1])
        
        for b in blocks:
            text = b[4].strip()
            if not text: continue
            
            # Simple RegEx heuristics to detect structure
            is_q_start = re.match(r'^(Q\s*\.?\s*\d+|Question\s*\d+|\d+\.)', text, re.I)
            is_opt_start = re.match(r'^[\(]?[A-D][\)\.]\s+', text, re.I)
            is_sol_start = re.match(r'^(Sol|Solution|Ans|Answer)\b', text, re.I)
            
            if is_q_start:
                if current_q: questions.append(current_q)
                current_q = {
                    "q_id": f"Pg{page_num+1}_Q{len(questions)+1}",
                    "text": text,
                    "options": [],
                    "solution": "",
                    "images": list(page_images), # Attach page images to this question
                    "state": "text"
                }
                page_images = [] # Consume images
            elif current_q:
                if is_sol_start or current_q["state"] == "solution":
                    current_q["state"] = "solution"
                    current_q["solution"] += "\n" + text
                elif is_opt_start or current_q["state"] == "options":
                    current_q["state"] = "options"
                    # Split options if multiple are on the same line (e.g. "(A) 1 (B) 2")
                    opts = re.split(r'(?=\([A-D]\)|[A-D]\.)', text)
                    current_q["options"].extend([o.strip() for o in opts if o.strip()])
                else:
                    current_q["text"] += "\n" + text
            
        # If there are trailing images that haven't been consumed, append them to the last question
        if current_q and page_images:
            current_q["images"].extend(page_images)

    if current_q: questions.append(current_q)
    
    logger.info(f"PDF Parse Complete. Found {len(questions)} potential questions.")
    
    # Save to Database
    docs = []
    for q in questions:
        # Link images via Markdown
        q_text = q["text"]
        for img_name in q["images"]:
            q_text += f"\n\n![Diagram](/unacademy_images/{img_name})"
            
        docs.append({
            "staging_id": new_id("stg"),
            "subject_id": subject_id,
            "extracted_id": q["q_id"],
            "question_text": q_text,
            "options": q["options"],
            "is_pyq": False,
            "year": None,
            "gate_set": None,
            "gate_qnum": None,
            "correct_answer": None,
            "solution_text": q["solution"] if q["solution"] else None,
            "status": "READY" if (q["solution"] or q["options"]) else "ORPHANED_QUESTION",
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc())
        })
        
    if docs:
        await db.staging_questions.insert_many(docs)
        logger.info(f"Successfully inserted {len(docs)} items into Staging Queue.")
    else:
        logger.warning("No questions found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=str, required=True, help="Path to the PDF file")
    args = parser.parse_args()
    
    # Motor handles event loops better when the client is used within the active loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(parse_unacademy_pdf(args.pdf))
