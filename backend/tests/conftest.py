import os
import sys
import time
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

# Setup sys.path to include backend/
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Define hardcoded tokens for testing
TEST_AUTH_TOKEN = "test_auth_token_xyz_123"
TEST_USER_TOKEN = "test_user_token_xyz_123"
TEST_PRIMARY_TOKEN = "test_primary_token_xyz_123"
TEST_SECONDARY_TOKEN = "test_secondary_token_xyz_123"

# Start uvicorn process reference
uvicorn_proc = None

async def seed_test_users():
    from app.core.config import Settings
    from app.core.ids import new_id
    from app.core.time import iso, now_utc
    from app.bootstrap.seed import seed_data
    from app.bootstrap import migrations

    settings = Settings(_env_file=str(backend_dir / ".env"))
    
    # Connect to MongoDB
    mongo_url = settings.MONGO_URL
    use_tls = "mongodb+srv://" in mongo_url or "replicaSet" in mongo_url or "ssl=true" in mongo_url.lower()
    client = AsyncIOMotorClient(
        mongo_url,
        tls=use_tls,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000
    )
    db = client[settings.DB_NAME]
    migrations.configure(db)
    await seed_data(db)
    
    # Define roles and users
    users = [
        {"user_id": "test_auth_user", "email": "auth@example.com", "name": "Test Auth User"},
        {"user_id": "test_normal_user", "email": "user@example.com", "name": "Test User"},
        {"user_id": "test_primary_user", "email": "primary@example.com", "name": "Test Primary User"},
        {"user_id": "test_secondary_user", "email": "secondary@example.com", "name": "Test Secondary User"},
    ]
    
    # Define sessions
    sessions = [
        {"user_id": "test_auth_user", "session_token": TEST_AUTH_TOKEN},
        {"user_id": "test_normal_user", "session_token": TEST_USER_TOKEN},
        {"user_id": "test_primary_user", "session_token": TEST_PRIMARY_TOKEN},
        {"user_id": "test_secondary_user", "session_token": TEST_SECONDARY_TOKEN},
    ]
    
    # Insert users
    for user in users:
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {            "$set": {
                "email": user["email"],
                "name": user["name"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
    # Insert sessions
    for sess in sessions:
        await db.user_sessions.update_one(
            {"session_token": sess["session_token"]},
            {"$set": {
                "user_id": sess["user_id"],
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
    await ensure_test_content(db, "test_auth_user")
    client.close()


async def ensure_test_content(db, user_id: str) -> None:
    from app.core.ids import new_id
    from app.core.time import iso, now_utc

    subject = await db.subjects.find_one({}, {"_id": 0}, sort=[("order", 1)])
    if not subject:
        return
    topic = await db.topics.find_one(
        {"subject_id": subject["subject_id"]}, {"_id": 0}, sort=[("order", 1)]
    )
    if not topic:
        return

    existing_questions = await db.questions.count_documents(
        {"user_id": user_id, "source": "TEST_AUTOMATED"}
    )
    templates = [
        ("MCQ", ["A", "B", "C", "D"], "1"),
        ("MSQ", ["A", "B", "C", "D"], ["0", "2"]),
        ("NAT", None, "12"),
    ]
    for i in range(existing_questions, 12):
        question_type, options, answer = templates[i % len(templates)]
        await db.questions.insert_one({
            "question_id": new_id("q"),
            "user_id": user_id,
            "subject_id": subject["subject_id"],
            "topic_id": topic["topic_id"],
            "question_type": question_type,
            "question_text": f"Automated test {question_type} question {i + 1}",
            "options": options,
            "correct_answer": answer,
            "solution": "Automated test solution",
            "source": "TEST_AUTOMATED",
            "created_at": iso(now_utc()),
        })

    existing_pyqs = await db.pyqs.count_documents(
        {"user_id": user_id, "source": "TEST_AUTOMATED"}
    )
    if existing_pyqs == 0:
        await db.pyqs.insert_one({
            "pyq_id": new_id("pyq"),
            "user_id": user_id,
            "subject_id": subject["subject_id"],
            "topic_id": topic["topic_id"],
            "year": 2024,
            "question_type": "MCQ",
            "question_text": "Automated test PYQ question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "1",
            "solution": "Automated test PYQ solution",
            "source": "TEST_AUTOMATED",
            "created_at": iso(now_utc()),
        })

def pytest_sessionstart(session):
    global uvicorn_proc
    
    # 1. Seed database with test users and sessions
    asyncio.run(seed_test_users())
    
    # 2. Set tokens in environment variables
    os.environ["AUTH_TOKEN"] = TEST_AUTH_TOKEN
    os.environ["USER_TOKEN"] = TEST_USER_TOKEN
    os.environ["PRIMARY_TOKEN"] = TEST_PRIMARY_TOKEN
    os.environ["SECONDARY_TOKEN"] = TEST_SECONDARY_TOKEN
    
    # 3. Start the uvicorn server in the background
    print("\nStarting local FastAPI server for integration tests...")
    
    # Launch uvicorn
    uvicorn_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=str(backend_dir)
    )
    
    # 4. Wait for the server to be responsive
    api_url = "http://127.0.0.1:8001/api/health"
    retries = 80
    connected = False
    for i in range(retries):
        try:
            r = requests.get(api_url, timeout=1)
            if r.status_code == 200:
                connected = True
                print("FastAPI server started successfully and is responsive!")
                break
        except requests.RequestException:
            pass
        time.sleep(0.5)
        
    if not connected:
        uvicorn_proc.kill()
        raise RuntimeError("Failed to start FastAPI server for integration tests.")

def pytest_sessionfinish(session, exitstatus):
    global uvicorn_proc
    if uvicorn_proc:
        print("\nStopping local FastAPI server...")
        uvicorn_proc.terminate()
        try:
            uvicorn_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            uvicorn_proc.kill()
        print("FastAPI server stopped.")

