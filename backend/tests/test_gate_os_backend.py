"""Backend integration tests for GATE Study OS."""
import os
from typing import Dict, List, Any

import pytest
import requests

BASE_URL: str = os.environ.get(
    "REACT_APP_BACKEND_URL", "http://localhost:8000"
).rstrip("/")
API: str = f"{BASE_URL}/api"

# Tokens created via mongosh seed (see /app/memory/test_credentials.md)
ADMIN_TOKEN: str | None = os.environ.get("ADMIN_TOKEN")
USER_TOKEN: str | None = os.environ.get("USER_TOKEN")


@pytest.fixture(scope="session")
def admin_headers() -> Dict[str, str]:
    assert ADMIN_TOKEN, "ADMIN_TOKEN env required"
    return {"Authorization": f"Bearer {ADMIN_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def user_headers() -> Dict[str, str]:
    assert USER_TOKEN, "USER_TOKEN env required"
    return {"Authorization": f"Bearer {USER_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def subjects(admin_headers: Dict[str, str]) -> List[Dict[str, Any]]:
    r = requests.get(f"{API}/subjects")
    assert r.status_code == 200
    return r.json()["data"]


@pytest.fixture(scope="session")
def questions(admin_headers: Dict[str, str]) -> List[Dict[str, Any]]:
    r = requests.get(f"{API}/questions", headers=admin_headers)
    assert r.status_code == 200
    return r.json()["data"]["items"]


@pytest.fixture(scope="session")
def pyqs(admin_headers: Dict[str, str]) -> List[Dict[str, Any]]:
    r = requests.get(f"{API}/pyqs", headers=admin_headers)
    assert r.status_code == 200
    return r.json()["data"]["items"]


# --------- Public endpoints ---------
class TestPublic:
    def test_root(self) -> None:
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        body = r.json()
        assert body.get("service") == "gate-study-os"

    def test_subjects_list(self) -> None:
        r = requests.get(f"{API}/subjects")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 12
        assert {"subject_id", "name", "order"}.issubset(data[0].keys())

    def test_topics_for_subject(self, subjects: List[Dict[str, Any]]) -> None:
        sid = subjects[0]["subject_id"]
        r = requests.get(f"{API}/subjects/{sid}/topics")
        assert r.status_code == 200
        topics = r.json()["data"]
        assert isinstance(topics, list) and len(topics) > 0


# --------- Auth gating ---------
class TestAuthGating:
    def test_questions_requires_auth(self) -> None:
        r = requests.get(f"{API}/questions")
        assert r.status_code == 401

    def test_dashboard_requires_auth(self) -> None:
        r = requests.get(f"{API}/dashboard")
        assert r.status_code == 401

    def test_auth_me_with_token(self, admin_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/auth/me", headers=admin_headers)
        assert r.status_code == 200
        u = r.json()["data"]["user"]
        assert u["is_admin"]


# --------- Dashboard / Questions list ---------
class TestDashboardAndQuestions:
    def test_dashboard_summary(self, admin_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/dashboard", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()["data"]
        summary = d["summary"]
        for k in ["questions_solved", "pyqs_solved", "videos_completed",
                  "total_playlists", "question_accuracy", "pyq_accuracy",
                  "total_mistakes", "resources_uploaded"]:
            assert k in summary, f"missing {k}"
        assert len(d["subjects"]) == 12

    def test_questions_list_with_progress(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        assert len(questions) >= 12
        for q in questions:
            assert "user_progress" in q
            assert set(q["user_progress"].keys()) >= {"count", "correct", "last_correct"}


# --------- Attempt grading ---------
class TestAttempts:
    def test_mcq_correct(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        mcq = next(q for q in questions if q["question_type"] == "MCQ")
        r = requests.post(f"{API}/questions/{mcq['question_id']}/attempt",
                          headers=admin_headers,
                          json={"selected_answer": mcq["correct_answer"], "time_taken": 5})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["attempt"]["is_correct"]
        assert d["correct_answer"] == mcq["correct_answer"]
        assert d["solution"]

    def test_mcq_wrong(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        mcq = next(q for q in questions if q["question_type"] == "MCQ")
        wrong = "0" if mcq["correct_answer"] != "0" else "1"
        r = requests.post(f"{API}/questions/{mcq['question_id']}/attempt",
                          headers=admin_headers,
                          json={"selected_answer": wrong})
        assert r.status_code == 200
        assert not r.json()["data"]["attempt"]["is_correct"]

    def test_msq_exact_match(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        msq = next(q for q in questions if q["question_type"] == "MSQ")
        r = requests.post(f"{API}/questions/{msq['question_id']}/attempt",
                          headers=admin_headers,
                          json={"selected_answer": msq["correct_answer"]})
        assert r.status_code == 200
        assert r.json()["data"]["attempt"]["is_correct"]

    def test_msq_partial_wrong(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        msq = next(q for q in questions if q["question_type"] == "MSQ")
        partial = msq["correct_answer"][:-1] if len(msq["correct_answer"]) > 1 else ["9"]
        r = requests.post(f"{API}/questions/{msq['question_id']}/attempt",
                          headers=admin_headers, json={"selected_answer": partial})
        assert r.status_code == 200
        assert not r.json()["data"]["attempt"]["is_correct"]

    def test_nat_correct(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        nat = next(q for q in questions if q["question_type"] == "NAT")
        r = requests.post(f"{API}/questions/{nat['question_id']}/attempt",
                          headers=admin_headers,
                          json={"selected_answer": nat["correct_answer"]})
        assert r.status_code == 200
        assert r.json()["data"]["attempt"]["is_correct"]


# --------- Notes ---------
class TestNotes:
    def test_save_and_get_note(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        qid = questions[0]["question_id"]
        r = requests.post(f"{API}/questions/{qid}/notes", headers=admin_headers,
                          json={"note_content": "TEST_note content"})
        assert r.status_code == 200
        r2 = requests.get(f"{API}/questions/{qid}/notes", headers=admin_headers)
        assert r2.status_code == 200
        assert r2.json()["data"]["note_content"] == "TEST_note content"


# --------- Mistakes ---------
class TestMistakes:
    def test_create_list_delete_mistake(
        self, admin_headers: Dict[str, str], questions: List[Dict[str, Any]]
    ) -> None:
        qid = questions[0]["question_id"]
        r = requests.post(f"{API}/mistakes", headers=admin_headers,
                          json={"question_id": qid, "mistake_type": "Conceptual Gap",
                                "note": "TEST_mistake"})
        assert r.status_code == 200
        mid = r.json()["data"]["mistake_id"]
        rl = requests.get(f"{API}/mistakes", headers=admin_headers)
        assert rl.status_code == 200
        assert any(m["mistake_id"] == mid for m in rl.json()["data"])
        rd = requests.delete(f"{API}/mistakes/{mid}", headers=admin_headers)
        assert rd.status_code == 200
        assert rd.json()["data"]["deleted"] == 1


# --------- PYQs ---------
class TestPYQs:
    def test_pyq_attempt(
        self, admin_headers: Dict[str, str], pyqs: List[Dict[str, Any]]
    ) -> None:
        pyq = pyqs[0]
        r = requests.post(f"{API}/pyqs/{pyq['pyq_id']}/attempt",
                          headers=admin_headers,
                          json={"selected_answer": pyq["correct_answer"]})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["attempt"]["is_correct"]
        assert d["solution"]


# --------- Resources ---------
class TestResources:
    def test_create_list_delete_resource(
        self, admin_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        r = requests.post(f"{API}/resources", headers=admin_headers,
                          json={"subject_id": sid, "resource_type": "Notes",
                                "title": "TEST_Resource", "external_url": "https://example.com"})
        assert r.status_code == 200
        rid = r.json()["data"]["resource_id"]
        rl = requests.get(f"{API}/resources", headers=admin_headers)
        assert rl.status_code == 200
        assert any(x["resource_id"] == rid for x in rl.json()["data"])
        rd = requests.delete(f"{API}/resources/{rid}", headers=admin_headers)
        assert rd.status_code == 200
        assert rd.json()["data"]["deleted"] == 1


# --------- Analytics ---------
class TestAnalytics:
    def test_subject_analytics(
        self, admin_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = next(s["subject_id"] for s in subjects if s["name"] == "Operating Systems")
        r = requests.get(f"{API}/analytics/subject/{sid}", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list) and len(data) > 0
        for row in data:
            assert "topic" in row and "qb" in row and "pyq" in row
            assert "accuracy" in row["qb"]

    def test_topic_analytics(
        self, admin_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = next(s["subject_id"] for s in subjects if s["name"] == "Operating Systems")
        t = requests.get(f"{API}/subjects/{sid}/topics").json()["data"][0]
        r = requests.get(f"{API}/analytics/topic/{t['topic_id']}", headers=admin_headers)
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
        self, admin_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        r = requests.post(f"{API}/playlists/import", headers=admin_headers,
                          json={"youtube_url": "https://example.com/not-a-playlist",
                                "subject_id": sid})
        assert r.status_code == 400
        body = r.json()
        assert not body["success"]
        assert body["error"]["code"] == "invalid_url"


# --------- Admin gating ---------
class TestAdmin:
    def test_admin_create_question(
        self, admin_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        t = requests.get(f"{API}/subjects/{sid}/topics").json()["data"][0]
        payload: Dict[str, Any] = {
            "subject_id": sid, "topic_id": t["topic_id"],
            "question_type": "MCQ", "question_text": "TEST_What is 2+2?",
            "options": ["3", "4", "5", "6"], "correct_answer": "1",
            "solution": "Basic math", "difficulty": "Easy",
        }
        r = requests.post(f"{API}/admin/questions", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        qid = r.json()["data"]["question_id"]
        # cleanup
        requests.delete(f"{API}/admin/questions/{qid}", headers=admin_headers)

    def test_admin_rejects_non_admin(
        self, user_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        t = requests.get(f"{API}/subjects/{sid}/topics").json()["data"][0]
        payload: Dict[str, Any] = {
            "subject_id": sid, "topic_id": t["topic_id"],
            "question_type": "MCQ", "question_text": "TEST_blocked",
            "options": ["a", "b"], "correct_answer": "0",
            "solution": "x", "difficulty": "Easy",
        }
        r = requests.post(f"{API}/admin/questions", headers=user_headers, json=payload)
        assert r.status_code == 403
