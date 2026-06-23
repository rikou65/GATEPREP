\# PDF\_INGESTION\_REALITY.md



\## Purpose



This document describes the current PDF ingestion architecture, its limitations, and the intended future direction.



\---



\# Current Import Architecture



Two import engines currently exist.



\## Engine 1: OCR Pipeline



Route:



POST /api/admin/import/pdf



Engine:



ocr



Flow:



PDF

↓

PDFOrchestrator

↓

Gemini

↓

Structured Extraction

↓

staging\_questions

↓

Manual Approval

↓

questions / pyqs



\---



\## Engine 2: Llama Pipeline



Route:



POST /api/admin/import/pdf



Engine:



llama



Flow:



PDF

↓

PyMuPDF Image Extraction

↓

LlamaParse

↓

Markdown

↓

Gemini Structuring

↓

staging\_questions

↓

Manual Approval

↓

questions / pyqs



\---



\# Current Collections



Import jobs:



import\_jobs



Temporary review area:



staging\_questions



Production:



questions

pyqs



\---



\# Existing Strengths



The system already provides:



\* Import job tracking

\* Background processing

\* Staging queue

\* Manual review workflow

\* Separate Question/PYQ insertion



The staging architecture should be preserved.



\---



\# Existing Weaknesses



The extraction system currently relies heavily on LLM interpretation.



Observed failure areas:



\* Formula extraction

\* Symbol preservation

\* Diagram association

\* Question boundaries

\* Answer key matching

\* Topic mapping



\---



\# GATE Overflow Observations



Important:



GATE Overflow PDFs are digitally generated PDFs.



They are not scanned image PDFs.



The PDFs already contain:



\* Subject structure

\* Topic structure

\* Question numbering

\* Answer key sections



Future extraction systems should leverage existing structure before invoking LLMs.



\---



\# Future Direction



Preferred extraction order:



1\. Direct PDF text extraction

2\. Deterministic parsing

3\. Structural validation

4\. AI-assisted cleanup



Not:



PDF → AI → Structure



Instead:



PDF → Structure → AI Cleanup



\---



\# Staging Rules



Every imported item must pass through staging.



Never bypass staging and write directly into:



\* questions

\* pyqs



The review step is a core architectural decision.



\---



\# Topic Mapping Problem



Current approval flow may insert placeholder topic mappings.



Future ingestion improvements should:



\* map subject\_id correctly

\* map topic\_id correctly

\* validate mappings before approval



Topic mapping quality is critical for analytics accuracy.



\---



\# AI Usage Policy



AI should assist with:



\* Formula cleanup

\* Formatting

\* Diagram descriptions

\* Content normalization



AI should not be responsible for:



\* Subject detection

\* Topic detection

\* Question numbering

\* Answer-key matching



Prefer deterministic logic whenever possible.



