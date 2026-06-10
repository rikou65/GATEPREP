#!/usr/bin/env python3
"""
Backend testing script for GATE Study OS Phase A refactor.
Tests per-user content, filters, flags, CRUD, and ownership isolation.
"""
import os
import sys
import secrets
import datetime
import requests
from pymongo import MongoClient

# Configuration
BACKEND_URL = "https://app-163.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "gateprep"

# Test results tracking
test_results = []
failed_tests = []

def log_test(name, passed, details=""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    test_results.append({"name": name, "passed": passed, "details": details})
    if not passed:
        failed_tests.append({"name": name, "details": details})

def setup_test_session():
    """Create a test user and session in MongoDB, return session_token and user_id."""
    print("\n=== Setting up test session ===")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Find existing user (rikouharu@gmail.com as mentioned in review request)
    user = db.users.find_one({"email": "rikouharu@gmail.com"})
    if not user:
        print("ERROR: User rikouharu@gmail.com not found in database")
        sys.exit(1)
    
    user_id = user["user_id"]
    print(f"Found user: {user['email']} (user_id: {user_id})")
    
    # Create a test session
    session_token = secrets.token_urlsafe(32)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "+00:00"
    created_at = datetime.datetime.utcnow().isoformat() + "+00:00"
    
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": created_at,
    })
    print(f"Created session token: {session_token[:20]}...")
    
    return session_token, user_id, db

def test_auth_sanity(session_token):
    """Test 1: Auth sanity - GET /api/auth/me with and without cookie."""
    print("\n=== Test 1: Auth Sanity ===")
    
    # Test with valid cookie
    resp = requests.get(f"{BACKEND_URL}/auth/me", cookies={"session_token": session_token})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("user"):
            log_test("GET /auth/me with valid cookie", True, f"User: {data['data']['user'].get('email')}")
        else:
            log_test("GET /auth/me with valid cookie", False, f"Unexpected response: {data}")
    else:
        log_test("GET /auth/me with valid cookie", False, f"Status: {resp.status_code}, Body: {resp.text}")
    
    # Test without cookie
    resp = requests.get(f"{BACKEND_URL}/auth/me")
    if resp.status_code == 401:
        log_test("GET /auth/me without cookie returns 401", True)
    else:
        log_test("GET /auth/me without cookie returns 401", False, f"Status: {resp.status_code}, Body: {resp.text}")

def test_question_filters(session_token, db):
    """Test 2: Question filters - subject_id, attempted, result, flag."""
    print("\n=== Test 2: Question Filters ===")
    
    cookies = {"session_token": session_token}
    
    # Get all questions
    resp = requests.get(f"{BACKEND_URL}/questions", cookies=cookies)
    if resp.status_code != 200:
        log_test("GET /questions", False, f"Status: {resp.status_code}, Body: {resp.text}")
        return
    
    data = resp.json()
    total = data.get("data", {}).get("total", 0)
    items = data.get("data", {}).get("items", [])
    
    if total >= 12:
        log_test("GET /questions returns total≥12", True, f"Total: {total}")
    else:
        log_test("GET /questions returns total≥12", False, f"Total: {total}")
    
    if not items:
        print("No questions found, skipping filter tests")
        return
    
    # Test subject_id filter
    first_subject_id = items[0].get("subject_id")
    if first_subject_id:
        resp = requests.get(f"{BACKEND_URL}/questions?subject_id={first_subject_id}", cookies=cookies)
        if resp.status_code == 200:
            filtered = resp.json().get("data", {}).get("items", [])
            all_match = all(q.get("subject_id") == first_subject_id for q in filtered)
            log_test("GET /questions?subject_id filters correctly", all_match, 
                    f"Filtered count: {len(filtered)}")
        else:
            log_test("GET /questions?subject_id filters correctly", False, 
                    f"Status: {resp.status_code}")
    
    # Test attempted=false (initially all should be not attempted)
    resp = requests.get(f"{BACKEND_URL}/questions?attempted=false", cookies=cookies)
    if resp.status_code == 200:
        not_attempted = resp.json().get("data", {}).get("total", 0)
        log_test("GET /questions?attempted=false", True, f"Not attempted: {not_attempted}")
    else:
        log_test("GET /questions?attempted=false", False, f"Status: {resp.status_code}")
    
    # Post an attempt for the first question (wrong answer)
    first_q = items[0]
    question_id = first_q.get("question_id")
    correct_answer = first_q.get("correct_answer")
    
    # Determine wrong answer based on question type
    wrong_answer = "999"  # Default wrong answer
    if first_q.get("question_type") == "MCQ":
        # Pick a different option
        if correct_answer == "0":
            wrong_answer = "1"
        else:
            wrong_answer = "0"
    
    resp = requests.post(
        f"{BACKEND_URL}/questions/{question_id}/attempt",
        json={"selected_answer": wrong_answer, "time_taken": 10},
        cookies=cookies
    )
    if resp.status_code == 200:
        attempt_data = resp.json().get("data", {})
        is_correct = attempt_data.get("attempt", {}).get("is_correct", False)
        log_test("POST /questions/{id}/attempt (wrong answer)", not is_correct, 
                f"Attempt recorded, is_correct: {is_correct}")
    else:
        log_test("POST /questions/{id}/attempt (wrong answer)", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # Now post a correct attempt
    resp = requests.post(
        f"{BACKEND_URL}/questions/{question_id}/attempt",
        json={"selected_answer": correct_answer, "time_taken": 15},
        cookies=cookies
    )
    if resp.status_code == 200:
        attempt_data = resp.json().get("data", {})
        is_correct = attempt_data.get("attempt", {}).get("is_correct", False)
        log_test("POST /questions/{id}/attempt (correct answer)", is_correct, 
                f"Attempt recorded, is_correct: {is_correct}")
    else:
        log_test("POST /questions/{id}/attempt (correct answer)", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # Test attempted=true (should include the question we just attempted)
    resp = requests.get(f"{BACKEND_URL}/questions?attempted=true", cookies=cookies)
    if resp.status_code == 200:
        attempted = resp.json().get("data", {}).get("items", [])
        attempted_ids = [q.get("question_id") for q in attempted]
        if question_id in attempted_ids:
            log_test("GET /questions?attempted=true includes attempted question", True)
        else:
            log_test("GET /questions?attempted=true includes attempted question", False, 
                    f"Question {question_id} not in attempted list")
    else:
        log_test("GET /questions?attempted=true", False, f"Status: {resp.status_code}")
    
    # Test result=correct (latest attempt was correct)
    resp = requests.get(f"{BACKEND_URL}/questions?attempted=true&result=correct", cookies=cookies)
    if resp.status_code == 200:
        correct_items = resp.json().get("data", {}).get("items", [])
        correct_ids = [q.get("question_id") for q in correct_items]
        if question_id in correct_ids:
            log_test("GET /questions?result=correct includes question with latest correct attempt", True)
        else:
            log_test("GET /questions?result=correct includes question with latest correct attempt", False,
                    f"Question {question_id} not in correct list")
    else:
        log_test("GET /questions?result=correct", False, f"Status: {resp.status_code}")
    
    # Test result=incorrect (should NOT include our question since latest is correct)
    resp = requests.get(f"{BACKEND_URL}/questions?attempted=true&result=incorrect", cookies=cookies)
    if resp.status_code == 200:
        incorrect_items = resp.json().get("data", {}).get("items", [])
        incorrect_ids = [q.get("question_id") for q in incorrect_items]
        if question_id not in incorrect_ids:
            log_test("GET /questions?result=incorrect excludes question with latest correct attempt", True)
        else:
            log_test("GET /questions?result=incorrect excludes question with latest correct attempt", False,
                    f"Question {question_id} should not be in incorrect list")
    else:
        log_test("GET /questions?result=incorrect", False, f"Status: {resp.status_code}")
    
    # Test flag=review with no flags set (should be empty)
    resp = requests.get(f"{BACKEND_URL}/questions?flag=review", cookies=cookies)
    if resp.status_code == 200:
        flagged = resp.json().get("data", {}).get("total", 0)
        # Note: There might be flags from previous tests, so we just check it doesn't error
        log_test("GET /questions?flag=review", True, f"Flagged count: {flagged}")
    else:
        log_test("GET /questions?flag=review", False, f"Status: {resp.status_code}")

def test_crud_operations(session_token, db):
    """Test 3: CRUD operations for questions and pyqs."""
    print("\n=== Test 3: CRUD Operations ===")
    
    cookies = {"session_token": session_token}
    
    # Get a subject and topic for creating questions
    subjects = db.subjects.find_one({})
    topics = db.topics.find_one({"subject_id": subjects["subject_id"]})
    
    if not subjects or not topics:
        log_test("CRUD setup", False, "No subjects/topics found")
        return
    
    # POST /questions - create a new question
    new_question = {
        "subject_id": subjects["subject_id"],
        "topic_id": topics["topic_id"],
        "question_type": "MCQ",
        "question_text": "What is the capital of India?",
        "options": ["Mumbai", "New Delhi", "Kolkata", "Chennai"],
        "correct_answer": "1",
        "solution": "New Delhi is the capital of India.",
        "difficulty": "Easy",
        "source": "Test"
    }
    
    resp = requests.post(f"{BACKEND_URL}/questions", json=new_question, cookies=cookies)
    if resp.status_code == 200:
        created = resp.json().get("data", {})
        question_id = created.get("question_id")
        log_test("POST /questions creates new question", True, f"Created question_id: {question_id}")
    else:
        log_test("POST /questions creates new question", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
        return
    
    # Verify it appears in GET /questions
    resp = requests.get(f"{BACKEND_URL}/questions", cookies=cookies)
    if resp.status_code == 200:
        items = resp.json().get("data", {}).get("items", [])
        question_ids = [q.get("question_id") for q in items]
        if question_id in question_ids:
            log_test("Created question appears in GET /questions", True)
        else:
            log_test("Created question appears in GET /questions", False)
    
    # PUT /questions/{id} - update the question
    resp = requests.put(
        f"{BACKEND_URL}/questions/{question_id}",
        json={"question_text": "What is the capital city of India?"},
        cookies=cookies
    )
    if resp.status_code == 200:
        updated = resp.json().get("data", {})
        if updated.get("question_text") == "What is the capital city of India?":
            log_test("PUT /questions/{id} updates question", True)
        else:
            log_test("PUT /questions/{id} updates question", False, 
                    f"Text not updated: {updated.get('question_text')}")
    else:
        log_test("PUT /questions/{id} updates question", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # POST an attempt for this question before deleting
    resp = requests.post(
        f"{BACKEND_URL}/questions/{question_id}/attempt",
        json={"selected_answer": "1", "time_taken": 5},
        cookies=cookies
    )
    attempt_created = resp.status_code == 200
    
    # DELETE /questions/{id}
    resp = requests.delete(f"{BACKEND_URL}/questions/{question_id}", cookies=cookies)
    if resp.status_code == 200:
        deleted = resp.json().get("data", {}).get("deleted", 0)
        if deleted == 1:
            log_test("DELETE /questions/{id} deletes question", True)
        else:
            log_test("DELETE /questions/{id} deletes question", False, f"Deleted count: {deleted}")
    else:
        log_test("DELETE /questions/{id} deletes question", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # Verify it's gone from GET /questions
    resp = requests.get(f"{BACKEND_URL}/questions", cookies=cookies)
    if resp.status_code == 200:
        items = resp.json().get("data", {}).get("items", [])
        question_ids = [q.get("question_id") for q in items]
        if question_id not in question_ids:
            log_test("Deleted question not in GET /questions", True)
        else:
            log_test("Deleted question not in GET /questions", False)
    
    # Verify attempts are also deleted
    if attempt_created:
        attempts_count = db.question_attempts.count_documents({"question_id": question_id})
        if attempts_count == 0:
            log_test("DELETE cascades to question_attempts", True)
        else:
            log_test("DELETE cascades to question_attempts", False, 
                    f"Found {attempts_count} attempts still in DB")
    
    # Test PYQ CRUD (similar to questions)
    new_pyq = {
        "subject_id": subjects["subject_id"],
        "topic_id": topics["topic_id"],
        "question_type": "MCQ",
        "question_text": "GATE 2024: What is the time complexity of merge sort?",
        "options": ["O(n)", "O(n log n)", "O(n^2)", "O(log n)"],
        "correct_answer": "1",
        "solution": "Merge sort has O(n log n) time complexity.",
        "difficulty": "Easy",
        "source": "GATE 2024",
        "year": 2024
    }
    
    resp = requests.post(f"{BACKEND_URL}/pyqs", json=new_pyq, cookies=cookies)
    if resp.status_code == 200:
        created = resp.json().get("data", {})
        pyq_id = created.get("pyq_id")
        log_test("POST /pyqs creates new PYQ", True, f"Created pyq_id: {pyq_id}")
        
        # Update PYQ
        resp = requests.put(
            f"{BACKEND_URL}/pyqs/{pyq_id}",
            json={"question_text": "GATE 2024: Time complexity of merge sort?"},
            cookies=cookies
        )
        if resp.status_code == 200:
            log_test("PUT /pyqs/{id} updates PYQ", True)
        else:
            log_test("PUT /pyqs/{id} updates PYQ", False, f"Status: {resp.status_code}")
        
        # Delete PYQ
        resp = requests.delete(f"{BACKEND_URL}/pyqs/{pyq_id}", cookies=cookies)
        if resp.status_code == 200:
            log_test("DELETE /pyqs/{id} deletes PYQ", True)
        else:
            log_test("DELETE /pyqs/{id} deletes PYQ", False, f"Status: {resp.status_code}")
    else:
        log_test("POST /pyqs creates new PYQ", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")

def test_flags(session_token, db):
    """Test 4: Flag operations."""
    print("\n=== Test 4: Flag Operations ===")
    
    cookies = {"session_token": session_token}
    
    # Get a question to flag
    resp = requests.get(f"{BACKEND_URL}/questions", cookies=cookies)
    if resp.status_code != 200:
        log_test("Flag test setup", False, "Could not get questions")
        return
    
    items = resp.json().get("data", {}).get("items", [])
    if not items:
        log_test("Flag test setup", False, "No questions available")
        return
    
    question_id = items[0].get("question_id")
    
    # POST flag with type "review"
    resp = requests.post(
        f"{BACKEND_URL}/questions/{question_id}/flag",
        json={"flag_type": "review"},
        cookies=cookies
    )
    if resp.status_code == 200:
        flags = resp.json().get("data", {}).get("flags", [])
        if "review" in flags:
            log_test("POST /questions/{id}/flag with review", True, f"Flags: {flags}")
        else:
            log_test("POST /questions/{id}/flag with review", False, f"Flags: {flags}")
    else:
        log_test("POST /questions/{id}/flag with review", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # POST flag with type "important"
    resp = requests.post(
        f"{BACKEND_URL}/questions/{question_id}/flag",
        json={"flag_type": "important"},
        cookies=cookies
    )
    if resp.status_code == 200:
        flags = resp.json().get("data", {}).get("flags", [])
        if "review" in flags and "important" in flags:
            log_test("POST /questions/{id}/flag with important", True, f"Flags: {flags}")
        else:
            log_test("POST /questions/{id}/flag with important", False, f"Flags: {flags}")
    else:
        log_test("POST /questions/{id}/flag with important", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # GET /questions?flag=review should include this question
    resp = requests.get(f"{BACKEND_URL}/questions?flag=review", cookies=cookies)
    if resp.status_code == 200:
        flagged = resp.json().get("data", {}).get("items", [])
        flagged_ids = [q.get("question_id") for q in flagged]
        if question_id in flagged_ids:
            log_test("GET /questions?flag=review includes flagged question", True)
        else:
            log_test("GET /questions?flag=review includes flagged question", False)
    else:
        log_test("GET /questions?flag=review", False, f"Status: {resp.status_code}")
    
    # DELETE flag type "review"
    resp = requests.delete(
        f"{BACKEND_URL}/questions/{question_id}/flag/review",
        cookies=cookies
    )
    if resp.status_code == 200:
        flags = resp.json().get("data", {}).get("flags", [])
        if "review" not in flags and "important" in flags:
            log_test("DELETE /questions/{id}/flag/review removes flag", True, f"Flags: {flags}")
        else:
            log_test("DELETE /questions/{id}/flag/review removes flag", False, f"Flags: {flags}")
    else:
        log_test("DELETE /questions/{id}/flag/review removes flag", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")
    
    # Test invalid flag type
    resp = requests.post(
        f"{BACKEND_URL}/questions/{question_id}/flag",
        json={"flag_type": "foo"},
        cookies=cookies
    )
    if resp.status_code == 400:
        error = resp.json().get("error", {})
        if error.get("code") == "invalid_flag":
            log_test("POST /questions/{id}/flag with invalid type returns 400", True)
        else:
            log_test("POST /questions/{id}/flag with invalid type returns 400", False, 
                    f"Error code: {error.get('code')}")
    else:
        log_test("POST /questions/{id}/flag with invalid type returns 400", False, 
                f"Status: {resp.status_code}")

def test_ownership_isolation(session_token, db):
    """Test 5: Ownership isolation - cross-user filtering."""
    print("\n=== Test 5: Ownership Isolation ===")
    
    # Create a second fake user
    user2_id = f"user_{secrets.token_hex(8)}"
    db.users.insert_one({
        "user_id": user2_id,
        "email": f"test_{secrets.token_hex(4)}@example.com",
        "name": "Test User 2",
        "picture": "",
        "is_admin": False,
        "created_at": datetime.datetime.utcnow().isoformat() + "+00:00"
    })
    
    # Create a session for user2
    session_token2 = secrets.token_urlsafe(32)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "+00:00"
    db.user_sessions.insert_one({
        "user_id": user2_id,
        "session_token": session_token2,
        "expires_at": expires_at,
        "created_at": datetime.datetime.utcnow().isoformat() + "+00:00"
    })
    
    # GET /questions with user2's session (should return 0 items)
    resp = requests.get(f"{BACKEND_URL}/questions", cookies={"session_token": session_token2})
    if resp.status_code == 200:
        total = resp.json().get("data", {}).get("total", -1)
        if total == 0:
            log_test("Cross-user isolation: user2 sees 0 questions", True)
        else:
            log_test("Cross-user isolation: user2 sees 0 questions", False, f"Total: {total}")
    else:
        log_test("Cross-user isolation: user2 sees 0 questions", False, 
                f"Status: {resp.status_code}")
    
    # Same for PYQs
    resp = requests.get(f"{BACKEND_URL}/pyqs", cookies={"session_token": session_token2})
    if resp.status_code == 200:
        total = resp.json().get("data", {}).get("total", -1)
        if total == 0:
            log_test("Cross-user isolation: user2 sees 0 pyqs", True)
        else:
            log_test("Cross-user isolation: user2 sees 0 pyqs", False, f"Total: {total}")
    else:
        log_test("Cross-user isolation: user2 sees 0 pyqs", False, 
                f"Status: {resp.status_code}")
    
    # Cleanup
    db.users.delete_one({"user_id": user2_id})
    db.user_sessions.delete_one({"user_id": user2_id})

def test_drive_sync(session_token):
    """Test 6: Drive sync endpoint."""
    print("\n=== Test 6: Drive Sync ===")
    
    cookies = {"session_token": session_token}
    
    # POST /drive/sync
    resp = requests.post(f"{BACKEND_URL}/drive/sync", cookies=cookies)
    if resp.status_code == 200:
        result = resp.json().get("data", {})
        # Should return synced, skipped, and possibly error or unknown_subjects
        if "synced" in result and "skipped" in result:
            log_test("POST /api/drive/sync returns valid response", True, 
                    f"Synced: {result.get('synced')}, Skipped: {result.get('skipped')}, Error: {result.get('error', 'none')}")
        else:
            log_test("POST /api/drive/sync returns valid response", False, f"Result: {result}")
    else:
        log_test("POST /api/drive/sync does not 500", resp.status_code != 500, 
                f"Status: {resp.status_code}, Body: {resp.text}")

def test_admin_endpoints(session_token):
    """Test 7: Admin endpoints no longer return 403."""
    print("\n=== Test 7: Admin Endpoints (No 403) ===")
    
    cookies = {"session_token": session_token}
    
    # GET /admin/users
    resp = requests.get(f"{BACKEND_URL}/admin/users", cookies=cookies)
    if resp.status_code == 200:
        users = resp.json().get("data", [])
        log_test("GET /admin/users returns 200 (not 403)", True, f"Users count: {len(users)}")
    else:
        log_test("GET /admin/users returns 200 (not 403)", False, 
                f"Status: {resp.status_code}, Body: {resp.text}")

def test_migration_idempotency(db):
    """Test 8: Migration idempotency - all questions/pyqs have user_id."""
    print("\n=== Test 8: Migration Idempotency ===")
    
    # Check questions without user_id
    count = db.questions.count_documents({"user_id": {"$exists": False}})
    if count == 0:
        log_test("All questions have user_id", True)
    else:
        log_test("All questions have user_id", False, f"Found {count} questions without user_id")
    
    # Check pyqs without user_id
    count = db.pyqs.count_documents({"user_id": {"$exists": False}})
    if count == 0:
        log_test("All pyqs have user_id", True)
    else:
        log_test("All pyqs have user_id", False, f"Found {count} pyqs without user_id")

def print_summary():
    """Print test summary."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)
    
    print(f"\nTotal: {total} tests")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    
    if failed_tests:
        print("\n" + "="*60)
        print("FAILED TESTS DETAILS")
        print("="*60)
        for test in failed_tests:
            print(f"\n❌ {test['name']}")
            if test['details']:
                print(f"   {test['details']}")
    
    print("\n" + "="*60)
    
    return len(failed_tests) == 0

def main():
    """Run all tests."""
    print("="*60)
    print("GATE Study OS - Phase A Backend Testing")
    print("="*60)
    
    try:
        # Setup
        session_token, user_id, db = setup_test_session()
        
        # Run tests
        test_auth_sanity(session_token)
        test_question_filters(session_token, db)
        test_crud_operations(session_token, db)
        test_flags(session_token, db)
        test_ownership_isolation(session_token, db)
        test_drive_sync(session_token)
        test_admin_endpoints(session_token)
        test_migration_idempotency(db)
        
        # Summary
        all_passed = print_summary()
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
