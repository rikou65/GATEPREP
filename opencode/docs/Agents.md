\# AGENTS.md



\# GATE Study OS



\## Purpose



GATE Study OS is a personal GATE CSE preparation platform.



The system manages:



\* Subjects

\* Topics

\* Question Bank

\* PYQs

\* Playlists

\* Resources

\* Mistake Tracking

\* Analytics

\* PDF Ingestion



The platform is designed for structured self-study.



\---



\# Read This First



Before making any changes:



1\. Read existing code before introducing new architecture.

2\. Extend existing systems instead of creating parallel systems.

3\. Preserve user-scoped data ownership.

4\. Preserve Question Bank and PYQ separation.

5\. Preserve staging review workflow.

6\. Prefer deterministic solutions over AI when structure already exists.



\---



\# Tech Stack



\## Frontend



\* React

\* React Router

\* React Query

\* Tailwind CSS



\## Backend



\* FastAPI



\## Database



\* MongoDB



\## Storage



\* Google Drive



\---



\# Core Data Model



\## Hierarchy



Subject

└── Topic



Questions and PYQs belong to Topics.



Topics belong to Subjects.



\---



\## Question Bank



Question fields:



\* question\_id

\* subject\_id

\* topic\_id

\* question\_type

\* question\_text

\* options

\* correct\_answer

\* solution


Solution may not always exist.



Question attempts are stored separately.



Question notes are stored separately.



Question flags are stored separately.



\---



\## PYQs



PYQs are separate from Question Bank.



Additional fields:



\* year

\* gate\_set

\* gate\_qnum



PYQ attempts are stored separately.



PYQ analytics are calculated separately.



Never merge Question Bank and PYQs.



\---



\# User Model



This is a user-owned study system.



All study artifacts are scoped by:



user\_id



Examples:



\* questions

\* pyqs

\* attempts

\* notes

\* flags

\* playlists

\* resources

\* mistakes



Never expose data across users.



Always filter user-owned content by user\_id.



\---



\# Analytics Rules



Question analytics use:



question\_attempts



PYQ analytics use:



pyq\_attempts



Question accuracy and PYQ accuracy are independent.



Question progress and PYQ progress are independent.



Do not merge them.



\---



\# Playlist System



Playlists are imported from YouTube.



Data model:



Playlist

└── Videos

└── Video Progress



Playlists belong to a subject.



Playlist completion does NOT affect:



\* Question progress

\* PYQ progress

\* Analytics



\---



\# Resource System



Resources support:



\* Google Drive files

\* External URLs



Primary storage:



Google Drive



Resource metadata:



resources collection



Resource notes:



resource\_notes collection



Drive credentials:



drive\_credentials collection



\---



\# Collections



users



user\_sessions



subjects



topics



questions



question\_attempts



question\_notes



question\_flags



pyqs



pyq\_attempts



pyq\_flags



mistakes



playlists



videos



video\_progress



resources



resource\_notes



drive\_credentials



import\_jobs



staging\_questions



\---



\# Backend Routers



core.py



Authentication

Subjects

Topics



\---



practice.py



Question Bank

PYQs

Attempts

Notes

Flags

Mistakes



\---



playlists.py



YouTube playlist import

Video progress



\---



resources.py



Google Drive integration

Resources

Resource notes



\---



analytics.py



Dashboard

Subject analytics



\---



admin\_staging.py



PDF import

Import jobs

Staging queue

Approval workflow



\---



\# PDF Ingestion System



Current engines:



1\. OCR

2\. Llama



OCR Flow:



PDF

↓

PDFOrchestrator

↓

Gemini

↓

Structured Extraction

↓

Staging



Llama Flow:



PDF

↓

PyMuPDF Image Extraction

↓

LlamaParse

↓

Gemini

↓

Staging



All imported content must enter staging before production.



Never bypass staging.



\---



\# Staging Workflow



PDF

↓

import\_jobs

↓

staging\_questions

↓

Manual Review

↓

questions OR pyqs



Staging is a core architectural decision.



Preserve it.



\---



\# Current PDF Ingestion Reality



Current import system depends heavily on AI extraction.



Known problem areas:



\* Formula extraction

\* Symbol preservation

\* Diagram association

\* Question boundaries

\* Answer-key matching

\* Topic mapping



Important:



GATE Overflow PDFs are digitally generated PDFs.



They already contain:



\* Subjects

\* Topics

\* Question numbering

\* Answer keys



Future improvements should prioritize deterministic parsing before AI extraction.



Preferred direction:



PDF

↓

Direct Text Extraction

↓

Deterministic Parsing

↓

Validation

↓

AI Cleanup



Not:



PDF

↓

AI

↓

Structure Detection



\---



\# Known Issues



\## Google Drive OAuth



User reports:



"Drive connection failed"



Relevant routes:



\* /drive/connect

\* /drive/callback

\* /drive/status

\* /drive/sync



Investigate configuration and callback flow before redesigning Drive integration.



Likely areas:



\* OAuth configuration

\* Redirect URI mismatch

\* Token exchange

\* Frontend callback handling



\---



\## Topic Mapping During Import



Current staging approval may insert imported content with placeholder topic mappings.



This can reduce analytics quality.



Future ingestion improvements should ensure:



\* valid subject\_id

\* valid topic\_id

\* validated mappings before approval



\---



\# Development Rules



Always:



\* Reuse existing collections.

\* Reuse existing routes.

\* Preserve user\_id isolation.

\* Preserve Question Bank and PYQ separation.

\* Preserve staging workflow.

\* Preserve analytics assumptions.

\* Prefer deterministic parsing over AI when possible.



Never:



\* Merge Question Bank and PYQs.

\* Remove staging review.

\* Introduce shared study data.

\* Store user study data globally.

\* Replace working systems without understanding their purpose.

\* Create parallel implementations of existing features.



When uncertain:



Read existing code before introducing new architecture.



