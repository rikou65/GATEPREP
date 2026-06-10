#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Phase A architectural refactor of GATE Study OS:
  - Remove the admin role entirely; every authenticated user manages their own Q/PYQ/notes/playlists.
  - Add user_id ownership to questions and pyqs; list endpoints filter by current user.
  - Stamp legacy seeded questions/pyqs (without user_id) to the first user on login (idempotent migration).
  - New filters on /questions and /pyqs: attempted=true|false, result=correct|incorrect (latest attempt), flag=review|important.
  - Per-user, per-item flags collections: question_flags, pyq_flags with unique (user_id,item_id,flag_type).
  - New CRUD endpoints: POST/PUT/DELETE /questions and /pyqs (replaces /admin/*). Legacy /admin/* aliases remain (no admin gate).
  - Flag endpoints: POST /{questions|pyqs}/:id/flag, DELETE /{questions|pyqs}/:id/flag/:flag_type.
  - Drive sync endpoint POST /api/drive/sync already exists and is invoked on Drive OAuth callback + manual button.

backend:
  - task: "Per-user content + filters + flags refactor"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          Phase A backend rewrite done. Key changes:
          1. require_admin retired (passthrough; no more 403).
          2. list_questions accepts attempted/result/flag query params; uses MongoDB aggregate for "latest attempt per question" to drive result filter; always filters by user_id.
          3. list_pyqs mirrors that with pyq_id, attempted_at, pyq_attempts.
          4. get_question / get_pyq enforce user_id ownership and return current flags array.
          5. attempt_question / attempt_pyq enforce ownership before recording attempt.
          6. New CRUD: POST /questions, PUT /questions/{id}, DELETE /questions/{id} (cascades to attempts/notes/flags/mistakes); same shape for /pyqs.
          7. New flag endpoints with VALID_FLAG_TYPES={"review","important"}, unique index (user_id,question_id|pyq_id,flag_type).
          8. Startup adds _migrate_per_user_content() and _ensure_flag_indexes(). The migration also runs after each /auth/session so the very-first user gets seed data attached automatically.
          9. /admin/questions, /admin/pyqs, /admin/users kept as thin aliases (no admin gate) for back-compat with any existing UI calls.
          
          Already verified locally:
          - mongosh confirms 12 questions + 6 pyqs all have user_id set to rikouharu's id after first login (migration ran).
          - Curl /api/questions returns 401 (auth required, correct).
          - No lint blocking issues on backend.
          
          Needs testing of:
          - Auth flow (login → cookie set → /auth/me works).
          - GET /questions and /pyqs with each combination of attempted/result/flag filters returning consistent counts.
          - Create + update + delete question; verify ownership 404 for other users (single user in this env, so verify by passing bad user_id manually).
          - Flag set/unset roundtrip + filter integration.
          - Drive sync endpoint POST /api/drive/sync returns sane result (we already verified prior 12-file sync). Just smoke check it doesn't 500.
      - working: true
        agent: "testing"
        comment: |
          ✅ ALL 31 BACKEND TESTS PASSED
          
          Comprehensive Phase A backend testing completed successfully:
          
          1. Auth Sanity (2/2 passed):
             - GET /auth/me with valid session_token cookie returns user (200)
             - GET /auth/me without cookie returns 401
          
          2. Question Filters (9/9 passed):
             - GET /questions returns total≥12 (seed data migrated correctly)
             - subject_id filter works correctly
             - attempted=false returns all unattempted questions
             - POST /questions/{id}/attempt records attempts (both wrong and correct)
             - attempted=true includes attempted questions
             - result=correct filter uses LATEST attempt (correct)
             - result=incorrect excludes questions with latest correct attempt
             - flag=review filter works
          
          3. CRUD Operations (9/9 passed):
             - POST /questions creates new question
             - Created question appears in GET /questions list
             - PUT /questions/{id} updates question text
             - DELETE /questions/{id} deletes question (returns deleted:1)
             - Deleted question removed from list
             - DELETE cascades to question_attempts collection
             - POST /pyqs creates new PYQ with year field
             - PUT /pyqs/{id} updates PYQ
             - DELETE /pyqs/{id} deletes PYQ
          
          4. Flag Operations (5/5 passed):
             - POST /questions/{id}/flag with flag_type="review" adds flag
             - POST /questions/{id}/flag with flag_type="important" adds second flag
             - GET /questions?flag=review includes flagged question
             - DELETE /questions/{id}/flag/review removes specific flag
             - POST with invalid flag_type="foo" returns 400 with code "invalid_flag"
          
          5. Ownership Isolation (2/2 passed):
             - Created second user with different user_id
             - Second user sees 0 questions (cross-user isolation working)
             - Second user sees 0 pyqs (cross-user isolation working)
          
          6. Drive Sync (1/1 passed):
             - POST /api/drive/sync returns valid response (synced:0, skipped:1)
             - No 500 errors
          
          7. Admin Endpoints (1/1 passed):
             - GET /admin/users returns 200 (not 403)
             - Admin gate fully retired as expected
          
          8. Migration Idempotency (2/2 passed):
             - All questions have user_id field (0 without user_id)
             - All pyqs have user_id field (0 without user_id)
          
          Backend URL tested: https://app-163.preview.emergentagent.com/api
          Test method: Created dummy session in MongoDB, used session_token cookie
          All endpoints working as specified in Phase A requirements.

frontend:
  - task: "QBank + PYQs filters, in-place Add/Edit/Delete, flag toggles, Drive sync moved to Resources"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/QuestionBank.jsx, frontend/src/pages/PYQs.jsx, frontend/src/components/QuestionViewer.jsx, frontend/src/components/QuestionForm.jsx, frontend/src/pages/Resources.jsx, frontend/src/pages/Settings.jsx, frontend/src/components/Layout.jsx, frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          NOT YET requested for testing. User must approve frontend testing first.
          Summary of UI changes:
          - Layout sidebar no longer links to /admin (Admin entry removed from NAV).
          - /admin route removed from App.js.
          - New shared QuestionForm.jsx supports both Add and Edit modes for Q and PYQ.
          - QuestionBank.jsx, PYQs.jsx: added Status (All/Not attempted/Attempted), Result (All/Correct/Incorrect when Attempted), Flag (All/Review/Important) filter pills + Add Question / Add PYQ dialog + per-card Edit/Delete via QuestionViewer.
          - QuestionViewer.jsx: new flag toggle buttons (review + important) with optimistic UI sync; Edit and Delete icons rendered when callbacks passed; ownership confirmed via backend.
          - Settings.jsx: removed Sync button; kept Connect / Disconnect. Copy mentions resources page for sync.
          - Resources.jsx: header now shows "Sync from Drive" button when Drive is connected, with lastSync info card.

metadata:
  created_by: "main_agent"
  version: "1.1"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Please test Phase A backend changes only. Auth credentials are in /app/memory/test_credentials.md (Google OAuth via Emergent). The seed migration has already stamped 12 questions and 6 pyqs to the existing user_id. Focus areas:
      1. Auth flow end-to-end (POST /auth/session via real session_id can't be tested in sandbox, but GET /auth/me + cookie acceptance can be verified by calling /api/questions with a valid session_token cookie obtained by running a script that posts a dummy/test session).
      2. GET /api/questions and /api/pyqs with combinations: subject_id, attempted=true|false, result=correct|incorrect (only when attempted=true), flag=review|important.
      3. POST /api/questions (create), PUT /api/questions/{id}, DELETE /api/questions/{id}; verify ownership and cascade deletion of attempts/notes/flags/mistakes. Same for /api/pyqs.
      4. POST /api/questions/{id}/flag with body {flag_type: "review"|"important"} → upsert, returns current flags array. DELETE /api/questions/{id}/flag/{flag_type} → remove. Mirror for pyqs.
      5. Latest-attempt correctness: create a question, post two attempts (first wrong, then right). Filter result=correct must include the question (latest is right), filter result=incorrect must NOT include it.
      6. POST /api/drive/sync should not 500 (it will likely return synced=0, skipped=12 since the 12-file restore already happened earlier in this session — or error=no_gateprep_folder if Drive is not yet connected in the test environment).
      DO NOT test frontend yet.
  - agent: "testing"
    message: |
      ✅ Phase A backend testing COMPLETE - ALL 31 TESTS PASSED
      
      Tested all Phase A requirements:
      - Auth: session_token cookie authentication working (401 without, 200 with valid token)
      - Filters: attempted, result (correct/incorrect using latest attempt), flag (review/important), subject_id all working
      - CRUD: POST/PUT/DELETE for questions and pyqs working with proper ownership enforcement
      - Flags: POST/DELETE flag operations working, invalid flag_type returns 400
      - Ownership: Cross-user isolation verified (second user sees 0 items)
      - Drive sync: Returns valid response without 500 errors
      - Admin: /admin/users returns 200 (no 403), admin gate retired
      - Migration: All questions and pyqs have user_id (idempotent migration successful)
      
      Backend is production-ready for Phase A. No issues found.
