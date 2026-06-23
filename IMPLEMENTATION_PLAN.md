# GATE Study OS — Implementation Plan

> A pragmatic, sequenced engineering plan for the "Personal Study OS" phase. Re-prioritise at the start of each week.

---

## ✅ Phase 1: MVP Hardening (Completed)
- **High-Performance Analytics:** Moved accuracy and progress logic into MongoDB Aggregation Pipelines to support 5,000+ questions.
- **Memory-Safe Resources:** Implemented `StreamingResponse` for chunked PDF delivery (No server memory crashes).
- **Manual OAuth Fix:** Implemented direct code-for-token exchange for both Login and Drive to resolve PKCE/Verifier errors.
- **De-branding:** Completely removed all Emergent AI branding and replaced with a clean, personal UI.

---

## ✅ Phase 2: User Autonomy & Scaling (Completed)
- **Admin Role Retirement:** Removed `require_admin` gatekeeping. Every user manages their own bank.
- **Library Polish:** Added descending Year Dropdown (2026–2000) and perfected filter alignment (pl-3 / right-12px).
- **Dev-Bypass:** Added local demo login for instant testing without external dependencies.
- **Multi-tenant Indexing:** Verified `user_id` scoping on all CRUD operations.

---

## 🔴 Phase 5: PDF Import & OCR Pipeline (ACTIVE)
*The "Active Build" — leveraging Gemini for bulk data ingestion.*

### Goal: Ingest 5,000+ questions/concepts from GO-PDFs.
1. **Source Mapping:** Download and map topic-wise volumes from `GATEOverflow/GO-PDFs`.
2. **Gemini Extraction:**
   - Dual-mode extraction: **Key Concepts** (LaTeX summaries) + **Questions** (JSON blocks).
   - Automated syllabus mapping using LLM reasoning.
3. **Staging Review:**
   - Build a `/staging` UI to review, edit, and approve extracted items before they hit the main bank.
   - Duplicate detection using text-hashing.

---

## 🟡 Phase 6: Spaced Repetition (Upcoming)
*Transforming the Mistake Lab into a retention engine.*

1. **SM-2 Core:** Implement the SuperMemo-2 scheduling algorithm.
2. **Dynamic Review:** Re-order Mistake Lab by "Review Date" rather than creation date.
3. **Outcome Tracking:** Use "Ease Factor" to adjust future intervals after each review session.

---

## 🟢 Phase 7: Discovery & Global Search
*The "Notion-like" surface polish.*

1. **Cmd+K Search:** Unified search bar across Subjects, Topics, Resources, and Questions.
2. **LaTeX Engine:** Full system-wide KaTeX integration for high-fidelity math rendering.
3. **PWA Polish:** Offline support for the custom PDF Canvas reader.

---

## 💭 Exploratory Backlog
- AI conversational tutor (Chat with your notes).
- Streak and Daily Goal HUD.
- Calibration diagnostic quiz on boarding.

---

<p align="center">
  <em>Last updated: June 2026. Phase 5 is the active priority.</em>
</p>
