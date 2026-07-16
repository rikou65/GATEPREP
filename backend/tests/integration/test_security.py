"""Security-focused integration tests for GATEPREP."""
from pathlib import Path
from typing import Dict

import requests

from tests.support import API

BACKEND_DIR = Path(__file__).resolve().parents[2]


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
        import sys
        backend_dir = str(BACKEND_DIR)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        import asyncio

        from motor.motor_asyncio import AsyncIOMotorClient

        from app.core.config import Settings
        from app.core.ids import new_id
        from app.core.time import iso, now_utc

        settings = Settings(_env_file=str(BACKEND_DIR / ".env"))
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
        import sys
        backend_dir = str(BACKEND_DIR)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        import asyncio

        from motor.motor_asyncio import AsyncIOMotorClient

        from app.core.config import Settings

        settings = Settings(_env_file=str(BACKEND_DIR / ".env"))
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

