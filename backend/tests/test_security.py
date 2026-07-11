"""Security-focused integration tests for GATEPREP."""
import os
from typing import Dict, Any

import pytest
import requests

BASE_URL: str = os.environ.get(
    "VITE_BACKEND_URL", "http://localhost:8001"
).rstrip("/")
API: str = f"{BASE_URL}/api"

AUTH_TOKEN: str | None = os.environ.get("AUTH_TOKEN")
USER_TOKEN: str | None = os.environ.get("USER_TOKEN")
PRIMARY_TOKEN: str | None = os.environ.get("PRIMARY_TOKEN")
SECONDARY_TOKEN: str | None = os.environ.get("SECONDARY_TOKEN")


@pytest.fixture(scope="session")
def auth_headers() -> Dict[str, str]:
    assert AUTH_TOKEN, "AUTH_TOKEN env required"
    return {"Cookie": f"session_token={AUTH_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def primary_headers() -> Dict[str, str]:
    assert PRIMARY_TOKEN, "PRIMARY_TOKEN env required"
    return {"Cookie": f"session_token={PRIMARY_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def secondary_headers() -> Dict[str, str]:
    assert SECONDARY_TOKEN, "SECONDARY_TOKEN env required"
    return {"Cookie": f"session_token={SECONDARY_TOKEN}", "Content-Type": "application/json"}


# --------- OAuth state validation ---------
class TestOAuthState:
    def test_oauth_login_rejects_missing_state(self, auth_headers: Dict[str, str]) -> None:
        r = requests.post(f"{API}/auth/session", json={"code": "fake_code"})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "missing_state"

    def test_oauth_login_rejects_invalid_state(self, auth_headers: Dict[str, str]) -> None:
        r = requests.post(f"{API}/auth/session", json={"code": "fake_code", "state": "invalid_state_123"})
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "auth_failed"


# --------- Staging tenant isolation ---------
class TestStagingIsolation:
    STAGING_API = f"{API}/data/staging"

    def _insert_test_staging(self, user_id: str) -> str:
        """Insert a staging_questions document for a given user via the server's DB directly.
        We do this by importing the Motor client from conftest's approach.
        Returns the staging_id.
        """
        from pathlib import Path
        import sys
        backend_dir = str(Path(__file__).parent.parent)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from app.core.config import Settings
        from app.core.ids import new_id
        from app.core.time import iso, now_utc
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio

        settings = Settings(_env_file=str(Path(__file__).parent.parent / ".env"))
        use_tls = "mongodb+srv://" in settings.MONGO_URL
        client = AsyncIOMotorClient(
            settings.MONGO_URL,
            tls=use_tls,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000,
        )
        db = client[settings.DB_NAME]
        staging_id = new_id("stg")

        async def _insert():
            await db.staging_questions.insert_one({
                "staging_id": staging_id,
                "user_id": user_id,
                "subject_id": "test_subject",
                "question_text": "Test staging isolation question",
                "status": "READY",
                "question_type": "MCQ",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "solution_text": "Test solution",
                "created_at": iso(now_utc()),
            })
            client.close()

        asyncio.run(_insert())
        return staging_id

    def _cleanup_staging(self, staging_id: str) -> None:
        from pathlib import Path
        import sys
        backend_dir = str(Path(__file__).parent.parent)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from app.core.config import Settings
        from app.core.time import iso, now_utc
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio

        settings = Settings(_env_file=str(Path(__file__).parent.parent / ".env"))
        use_tls = "mongodb+srv://" in settings.MONGO_URL
        client = AsyncIOMotorClient(
            settings.MONGO_URL,
            tls=use_tls,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000,
        )
        db = client[settings.DB_NAME]

        async def _delete():
            await db.staging_questions.delete_one({"staging_id": staging_id})
            client.close()

        asyncio.run(_delete())

    def test_staging_list_only_own_items(
        self, primary_headers: Dict[str, str], secondary_headers: Dict[str, str]
    ) -> None:
        sid = self._insert_test_staging("test_primary_user")
        try:
            r2 = requests.get(self.STAGING_API, headers=secondary_headers)
            assert r2.status_code == 200
            secondary_ids = {x["staging_id"] for x in r2.json()["data"]}
            assert sid not in secondary_ids, "Secondary user should not see primary user's staging item"
        finally:
            self._cleanup_staging(sid)

    def test_staging_discard_rejects_other_users_item(
        self, primary_headers: Dict[str, str], secondary_headers: Dict[str, str]
    ) -> None:
        sid = self._insert_test_staging("test_primary_user")
        try:
            r = requests.delete(f"{self.STAGING_API}/{sid}", headers=secondary_headers)
            assert r.status_code == 404, "Secondary user should not be able to discard primary user's staging item"
        finally:
            self._cleanup_staging(sid)

