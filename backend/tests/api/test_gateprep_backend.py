"""Backend integration tests for GATEPREP."""
import asyncio
from pathlib import Path
from typing import Any, Dict, List

import requests
from motor.motor_asyncio import AsyncIOMotorClient

from tests.support import API

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_db(coro):
    return asyncio.run(coro)


async def _with_db(fn):
    from app.core.config import Settings

    settings = Settings(_env_file=str(BACKEND_DIR / ".env"))
    use_tls = "mongodb+srv://" in settings.MONGO_URL
    client = AsyncIOMotorClient(
        settings.MONGO_URL,
        tls=use_tls,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000,
    )
    try:
        return await fn(client[settings.DB_NAME])
    finally:
        client.close()


# --------- Public endpoints ---------
class TestPublic:
    def test_root(self) -> None:
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        body = r.json()
        assert body.get("service") == "gateprep"

    def test_topics_for_subject(self, subjects: List[Dict[str, Any]], auth_headers: Dict[str, str]) -> None:
        sid = subjects[0]["subject_id"]
        r = requests.get(f"{API}/subjects/{sid}/topics", headers=auth_headers)
        assert r.status_code == 200
        topics = r.json()["data"]
        assert isinstance(topics, list) and len(topics) > 0


# --------- Auth gating ---------
class TestAuthGating:
    def test_questions_requires_auth(self) -> None:
        r = requests.get(f"{API}/questions")
        assert r.status_code == 401
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == "http_error"
        assert body["error"]["message"] == "Not authenticated"

    def test_dashboard_requires_auth(self) -> None:
        r = requests.get(f"{API}/dashboard")
        assert r.status_code == 401

    def test_subjects_requires_auth(self) -> None:
        r = requests.get(f"{API}/subjects")
        assert r.status_code == 401

    def test_auth_me_with_token(self, auth_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/auth/me", headers=auth_headers)
        assert r.status_code == 200
        u = r.json()["data"]["user"]
        assert u.get("user_id")

    def test_dev_login_does_not_return_session_token(self) -> None:
        r = requests.post(f"{API}/auth/dev-login")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "session_token" not in data
        assert data["user"]["user_id"]


# --------- Dashboard / Questions list ---------
class TestDashboardAndQuestions:
    def test_dashboard_summary(self, auth_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/dashboard", headers=auth_headers)
        assert r.status_code == 200
        d = r.json()["data"]
        summary = d["summary"]
        for k in ["questions_solved", "pyqs_solved", "videos_completed",
                  "total_playlists", "question_accuracy", "pyq_accuracy",
                  "total_mistakes", "resources_uploaded"]:
            assert k in summary, f"missing {k}"
        assert len(d["subjects"]) == 12

    def test_questions_list_with_progress(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        assert len(questions) >= 12
        for q in questions:
            assert "user_progress" in q
            assert set(q["user_progress"].keys()) >= {"count", "correct", "last_correct"}

    def test_questions_pagination_contract(self, auth_headers: Dict[str, str]) -> None:
        first = requests.get(f"{API}/questions", headers=auth_headers, params={"limit": 5, "skip": 0})
        second = requests.get(f"{API}/questions", headers=auth_headers, params={"limit": 5, "skip": 5})

        assert first.status_code == 200
        assert second.status_code == 200
        first_data = first.json()["data"]
        second_data = second.json()["data"]

        assert first_data["total"] >= 12
        assert len(first_data["items"]) == 5
        assert len(second_data["items"]) == 5
        first_ids = {q["question_id"] for q in first_data["items"]}
        second_ids = {q["question_id"] for q in second_data["items"]}
        assert first_ids.isdisjoint(second_ids)


# --------- Attempt grading ---------
class TestAttempts:
    def test_mcq_correct(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        mcq = next(q for q in questions if q["question_type"] == "MCQ")
        r = requests.post(f"{API}/questions/{mcq['question_id']}/attempt",
                          headers=auth_headers,
                          json={"selected_answer": mcq["correct_answer"], "time_taken": 5})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["attempt"]["is_correct"]
        assert d["correct_answer"] == mcq["correct_answer"]
        assert d["solution"]

    def test_mcq_wrong(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        mcq = next(q for q in questions if q["question_type"] == "MCQ")
        wrong = "0" if mcq["correct_answer"] != "0" else "1"
        r = requests.post(f"{API}/questions/{mcq['question_id']}/attempt",
                          headers=auth_headers,
                          json={"selected_answer": wrong})
        assert r.status_code == 200
        assert not r.json()["data"]["attempt"]["is_correct"]

    def test_msq_exact_match(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        msq = next(q for q in questions if q["question_type"] == "MSQ")
        r = requests.post(f"{API}/questions/{msq['question_id']}/attempt",
                          headers=auth_headers,
                          json={"selected_answer": msq["correct_answer"]})
        assert r.status_code == 200
        assert r.json()["data"]["attempt"]["is_correct"]

    def test_msq_partial_wrong(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        msq = next(q for q in questions if q["question_type"] == "MSQ")
        partial = msq["correct_answer"][:-1] if len(msq["correct_answer"]) > 1 else ["9"]
        r = requests.post(f"{API}/questions/{msq['question_id']}/attempt",
                          headers=auth_headers, json={"selected_answer": partial})
        assert r.status_code == 200
        assert not r.json()["data"]["attempt"]["is_correct"]

    def test_nat_correct(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        nat = next(q for q in questions if q["question_type"] == "NAT")
        r = requests.post(f"{API}/questions/{nat['question_id']}/attempt",
                          headers=auth_headers,
                          json={"selected_answer": nat["correct_answer"]})
        assert r.status_code == 200
        assert r.json()["data"]["attempt"]["is_correct"]


# --------- Notes ---------
class TestNotes:
    def test_save_and_get_note(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        qid = questions[0]["question_id"]
        r = requests.post(f"{API}/questions/{qid}/notes", headers=auth_headers,
                          json={"note_content": "TEST_note content"})
        assert r.status_code == 200
        r2 = requests.get(f"{API}/questions/{qid}/notes", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["data"]["note_content"] == "TEST_note content"


# --------- Mistakes ---------
class TestMistakes:
    def test_create_list_delete_mistake(
        self, auth_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        qid = questions[0]["question_id"]
        r = requests.post(f"{API}/mistakes", headers=auth_headers,
                          json={"question_id": qid, "mistake_type": "Conceptual Gap",
                                "note": "TEST_mistake"})
        assert r.status_code == 200
        mid = r.json()["data"]["mistake_id"]
        rl = requests.get(f"{API}/mistakes", headers=auth_headers)
        assert rl.status_code == 200
        assert any(m["mistake_id"] == mid for m in rl.json()["data"])
        rd = requests.delete(f"{API}/mistakes/{mid}", headers=auth_headers)
        assert rd.status_code == 200
        assert rd.json()["data"]["deleted"] == 1


# --------- PYQs ---------
class TestPYQs:
    def test_pyq_attempt(
        self, auth_headers: Dict[str, str], pyqs: List[Dict[str, Any]]
    ) -> None:
        pyq = pyqs[0]
        r = requests.post(f"{API}/pyqs/{pyq['pyq_id']}/attempt",
                          headers=auth_headers,
                          json={"selected_answer": pyq["correct_answer"]})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["attempt"]["is_correct"]
        assert d["solution"]

    def test_pyqs_pagination_contract(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        topic = requests.get(f"{API}/subjects/{sid}/topics", headers=auth_headers).json()["data"][0]
        created_ids = []
        try:
            for i in range(3):
                payload: Dict[str, Any] = {
                    "subject_id": sid,
                    "topic_id": topic["topic_id"],
                    "year": 2024 - i,
                    "question_type": "MCQ",
                    "question_text": f"TEST_Paginated PYQ {i}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "0",
                    "solution": "Pagination test solution",
                    "source": "TEST_PAGINATION",
                }
                created = requests.post(f"{API}/pyqs", headers=auth_headers, json=payload)
                assert created.status_code == 200
                created_ids.append(created.json()["data"]["pyq_id"])

            first = requests.get(f"{API}/pyqs", headers=auth_headers, params={"limit": 2, "skip": 0})
            second = requests.get(f"{API}/pyqs", headers=auth_headers, params={"limit": 2, "skip": 2})

            assert first.status_code == 200
            assert second.status_code == 200
            first_data = first.json()["data"]
            second_data = second.json()["data"]

            assert first_data["total"] >= 4
            assert len(first_data["items"]) == 2
            assert len(second_data["items"]) == 2
            first_ids = {p["pyq_id"] for p in first_data["items"]}
            second_ids = {p["pyq_id"] for p in second_data["items"]}
            assert first_ids.isdisjoint(second_ids)
        finally:
            for pyq_id in created_ids:
                requests.delete(f"{API}/pyqs/{pyq_id}", headers=auth_headers)


# --------- Resources ---------
class TestResources:
    def test_create_list_delete_resource(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        r = requests.post(f"{API}/resources", headers=auth_headers,
                          json={"subject_id": sid, "resource_type": "Notes",
                                "title": "TEST_Resource", "external_url": "https://example.com"})
        assert r.status_code == 200
        rid = r.json()["data"]["resource_id"]
        rl = requests.get(f"{API}/resources", headers=auth_headers)
        assert rl.status_code == 200
        assert any(x["resource_id"] == rid for x in rl.json()["data"])
        rd = requests.delete(f"{API}/resources/{rid}", headers=auth_headers)
        assert rd.status_code == 200
        assert rd.json()["data"]["deleted"] == 1


# --------- Analytics ---------
class TestAnalytics:
    def test_subject_analytics(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = next(s["subject_id"] for s in subjects if s["name"] == "Operating Systems")
        r = requests.get(f"{API}/analytics/subject/{sid}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list) and len(data) > 0
        for row in data:
            assert "topic" in row and "qb" in row and "pyq" in row
            assert "accuracy" in row["qb"]

    def test_topic_analytics(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = next(s["subject_id"] for s in subjects if s["name"] == "Operating Systems")
        t = requests.get(f"{API}/subjects/{sid}/topics", headers=auth_headers).json()["data"][0]
        r = requests.get(f"{API}/analytics/topic/{t['topic_id']}", headers=auth_headers)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "qb" in d and "pyq" in d and "accuracy" in d["qb"]


# --------- Playlists ---------
class TestPlaylists:
    def test_empty_playlists(self, user_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/playlists", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["data"] == []

    def test_invalid_playlist_url(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        r = requests.post(f"{API}/playlists/import", headers=auth_headers,
                          json={"youtube_url": "https://example.com/not-a-playlist",
                                "subject_id": sid})
        assert r.status_code == 400
        body = r.json()
        assert not body["success"]
        assert body["error"]["code"] == "invalid_url"

    def test_progress_update_targets_only_active_video(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        from app.core.ids import new_id
        from app.core.time import iso, now_utc

        playlist_id = new_id("pl")
        video_a = new_id("vid")
        video_b = new_id("vid")
        subject_id = subjects[0]["subject_id"]

        async def seed(db):
            await db.playlists.insert_one({
                "playlist_id": playlist_id,
                "user_id": "test_auth_user",
                "subject_id": subject_id,
                "title": "TEST Progress Playlist",
                "youtube_playlist_id": "TEST_PROGRESS_PLAYLIST",
                "thumbnail_url": "",
                "created_at": iso(now_utc()),
            })
            await db.videos.insert_many([
                {
                    "video_id": video_a,
                    "playlist_id": playlist_id,
                    "youtube_video_id": "TEST_PROGRESS_A",
                    "title": "Video A",
                    "position": 0,
                    "duration": 600,
                },
                {
                    "video_id": video_b,
                    "playlist_id": playlist_id,
                    "youtube_video_id": "TEST_PROGRESS_B",
                    "title": "Video B",
                    "position": 1,
                    "duration": 600,
                },
            ])

        async def cleanup(db):
            await db.video_progress.delete_many({"video_id": {"$in": [video_a, video_b]}})
            await db.videos.delete_many({"playlist_id": playlist_id})
            await db.playlists.delete_one({"playlist_id": playlist_id})

        _run_db(_with_db(seed))
        try:
            first = requests.post(
                f"{API}/videos/{video_a}/progress",
                headers=auth_headers,
                json={"watch_percentage": 40, "watch_time": 240, "completed": False},
            )
            second = requests.post(
                f"{API}/videos/{video_b}/progress",
                headers=auth_headers,
                json={"watch_percentage": 100, "watch_time": 600, "completed": True},
            )

            assert first.status_code == 200
            assert second.status_code == 200

            playlist = requests.get(f"{API}/playlists/{playlist_id}", headers=auth_headers)
            assert playlist.status_code == 200
            videos = {v["video_id"]: v for v in playlist.json()["data"]["videos"]}

            assert videos[video_a]["progress"]["watch_percentage"] == 40
            assert videos[video_a]["progress"]["completed"] is False
            assert videos[video_b]["progress"]["watch_percentage"] == 100
            assert videos[video_b]["progress"]["completed"] is True
        finally:
            _run_db(_with_db(cleanup))


# --------- Question creation ---------
class TestQuestionCreation:
    def test_create_question(
        self, auth_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        t = requests.get(f"{API}/subjects/{sid}/topics", headers=auth_headers).json()["data"][0]
        payload: Dict[str, Any] = {
            "subject_id": sid, "topic_id": t["topic_id"],
            "question_type": "MCQ", "question_text": "TEST_What is 2+2?",
            "options": ["3", "4", "5", "6"], "correct_answer": "1",
            "solution": "Basic math",
        }
        r = requests.post(f"{API}/questions", headers=auth_headers, json=payload)
        assert r.status_code == 200, r.text
        qid = r.json()["data"]["question_id"]
        # cleanup
        requests.delete(f"{API}/questions/{qid}", headers=auth_headers)


