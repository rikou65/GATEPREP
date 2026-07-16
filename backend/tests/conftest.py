import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from tests.support import API, json_session_headers

# Setup sys.path to include backend/
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Define hardcoded tokens for testing
TEST_AUTH_TOKEN = "test_auth_token_xyz_123"
TEST_USER_TOKEN = "test_user_token_xyz_123"
TEST_PRIMARY_TOKEN = "test_primary_token_xyz_123"
TEST_SECONDARY_TOKEN = "test_secondary_token_xyz_123"

test_client = None
_original_requests = {}

async def seed_test_users():
    from app.bootstrap import migrations
    from app.bootstrap.seed import seed_data
    from app.core.config import Settings

    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("DB_NAME", "gateprep_test")

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
    await client.admin.command("ping")
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
    global test_client, _original_requests
    
    # 1. Seed database with test users and sessions
    try:
        asyncio.run(seed_test_users())
    except PyMongoError as exc:
        pytest.exit(
            "MongoDB is not available for backend tests. Start MongoDB on "
            "mongodb://localhost:27017 or set MONGO_URL/DB_NAME before running "
            f"pytest. Original error: {exc}",
            returncode=2,
        )
    
    # 2. Set tokens in environment variables
    os.environ["AUTH_TOKEN"] = TEST_AUTH_TOKEN
    os.environ["USER_TOKEN"] = TEST_USER_TOKEN
    os.environ["PRIMARY_TOKEN"] = TEST_PRIMARY_TOKEN
    os.environ["SECONDARY_TOKEN"] = TEST_SECONDARY_TOKEN

    from app.main import app

    test_client = TestClient(app)
    test_client.__enter__()
    _original_requests = {
        "request": requests.request,
        "get": requests.get,
        "post": requests.post,
        "delete": requests.delete,
    }

    def _client_request(method: str, url: str, **kwargs):
        parsed = urlsplit(str(url))
        path = parsed.path or "/"
        if parsed.query and "params" not in kwargs:
            path = f"{path}?{parsed.query}"

        kwargs.pop("timeout", None)
        if "allow_redirects" in kwargs:
            kwargs["follow_redirects"] = kwargs.pop("allow_redirects")

        return test_client.request(method, path, **kwargs)

    requests.request = _client_request
    requests.get = lambda url, **kwargs: _client_request("GET", url, **kwargs)
    requests.post = lambda url, **kwargs: _client_request("POST", url, **kwargs)
    requests.delete = lambda url, **kwargs: _client_request("DELETE", url, **kwargs)

def pytest_sessionfinish(session, exitstatus):
    global test_client, _original_requests

    for name, original in _original_requests.items():
        setattr(requests, name, original)
    _original_requests = {}

    if test_client:
        test_client.__exit__(None, None, None)
        test_client = None


@pytest.fixture(scope="session")
def auth_headers():
    return json_session_headers(TEST_AUTH_TOKEN)


@pytest.fixture(scope="session")
def user_headers():
    return json_session_headers(TEST_USER_TOKEN)


@pytest.fixture(scope="session")
def primary_headers():
    return json_session_headers(TEST_PRIMARY_TOKEN)


@pytest.fixture(scope="session")
def secondary_headers():
    return json_session_headers(TEST_SECONDARY_TOKEN)


@pytest.fixture(scope="session")
def subjects(auth_headers):
    r = requests.get(f"{API}/subjects", headers=auth_headers)
    assert r.status_code == 200
    return r.json()["data"]


@pytest.fixture(scope="session")
def questions(auth_headers):
    r = requests.get(f"{API}/questions", headers=auth_headers)
    assert r.status_code == 200
    return r.json()["data"]["items"]


@pytest.fixture(scope="session")
def pyqs(auth_headers):
    r = requests.get(f"{API}/pyqs", headers=auth_headers)
    assert r.status_code == 200
    return r.json()["data"]["items"]

