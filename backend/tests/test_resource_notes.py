"""Backend integration tests for Phase B: Resource Study Notes + Important Pages.

Covers:
- GET /api/resources/{rid}/notes (empty default, 404 not found / cross-user)
- POST /api/resources/{rid}/notes (content + important_pages; legacy int list, labelled
  dict list, dedupe/sort, drop <=0)
- POST /api/resources/{rid}/pages/toggle (add/remove, idempotency, bad_page)
- POST /api/resources/{rid}/pages/label (update, not_flagged, bad_page)
- DELETE /api/resources/{rid} cascades resource_notes
- GET /api/health
- Phase-A regression: /api/dashboard, GET /api/questions filters, POST /api/questions,
  POST /api/questions/{id}/flag
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest
import requests

BASE_URL: str = os.environ.get(
    "REACT_APP_BACKEND_URL", "http://localhost:8000"
).rstrip("/")
API: str = f"{BASE_URL}/api"

PRIMARY_TOKEN: str | None = os.environ.get("PRIMARY_TOKEN")
SECONDARY_TOKEN: str | None = os.environ.get("SECONDARY_TOKEN")


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def primary_headers() -> Dict[str, str]:
    assert PRIMARY_TOKEN, "PRIMARY_TOKEN env required"
    return {"Authorization": f"Bearer {PRIMARY_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def secondary_headers() -> Dict[str, str]:
    assert SECONDARY_TOKEN, "SECONDARY_TOKEN env required"
    return {"Authorization": f"Bearer {SECONDARY_TOKEN}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def subjects() -> List[Dict[str, Any]]:
    r = requests.get(f"{API}/subjects")
    assert r.status_code == 200
    return r.json()["data"]


def _create_resource(headers: Dict[str, str], sid: str, title: str) -> str:
    r = requests.post(
        f"{API}/resources",
        headers=headers,
        json={
            "subject_id": sid,
            "resource_type": "Notes",
            "title": title,
            "external_url": "https://example.com/test.pdf",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["resource_id"]


# ---------- /api/health ----------
class TestHealth:
    def test_health_endpoint(self) -> None:
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "ts" in body and isinstance(body["ts"], str) and "T" in body["ts"]


# ---------- Resource Notes (Phase B) ----------
class TestResourceNotes:
    def test_empty_notes_for_new_resource(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_empty_notes")
        try:
            r = requests.get(f"{API}/resources/{rid}/notes", headers=primary_headers)
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["content"] == ""
            assert d["important_pages"] == []
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_notes_404_for_missing_resource(self, primary_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/resources/res_does_not_exist/notes", headers=primary_headers)
        assert r.status_code == 404
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == "not_found"

    def test_notes_cross_user_isolation(
        self,
        primary_headers: Dict[str, str],
        secondary_headers: Dict[str, str],
        subjects: List[Dict[str, Any]],
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_cross_user")
        try:
            # secondary user cannot read primary's resource notes
            r = requests.get(f"{API}/resources/{rid}/notes", headers=secondary_headers)
            assert r.status_code == 404
            assert r.json()["error"]["code"] == "not_found"
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_save_content_preserves_important_pages(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_save_content")
        try:
            # seed some important pages
            r0 = requests.post(
                f"{API}/resources/{rid}/notes",
                headers=primary_headers,
                json={"important_pages": [3, 9]},
            )
            assert r0.status_code == 200
            # now save only content
            r1 = requests.post(
                f"{API}/resources/{rid}/notes",
                headers=primary_headers,
                json={"content": "foo"},
            )
            assert r1.status_code == 200
            d = r1.json()["data"]
            assert d["content"] == "foo"
            # important_pages must remain intact
            assert d["important_pages"] == [
                {"page": 3, "label": ""},
                {"page": 9, "label": ""},
            ]
            # GET returns the same content
            r2 = requests.get(f"{API}/resources/{rid}/notes", headers=primary_headers)
            assert r2.status_code == 200
            d2 = r2.json()["data"]
            assert d2["content"] == "foo"
            assert d2["important_pages"] == d["important_pages"]
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_legacy_int_list_coerces(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_legacy_ints")
        try:
            r = requests.post(
                f"{API}/resources/{rid}/notes",
                headers=primary_headers,
                # include duplicates, zero, negative — should be dedup'd and dropped
                json={"important_pages": [12, 1, 5, 5, 0, -3, 12]},
            )
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["important_pages"] == [
                {"page": 1, "label": ""},
                {"page": 5, "label": ""},
                {"page": 12, "label": ""},
            ]
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_labelled_object_list_persists(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_labelled_objs")
        try:
            r = requests.post(
                f"{API}/resources/{rid}/notes",
                headers=primary_headers,
                json={
                    "important_pages": [
                        {"page": 3, "label": "intro"},
                        {"page": 7, "label": ""},
                    ]
                },
            )
            assert r.status_code == 200
            d = r.json()["data"]
            assert d["important_pages"] == [
                {"page": 3, "label": "intro"},
                {"page": 7, "label": ""},
            ]
            # Verify GET round-trip
            r2 = requests.get(f"{API}/resources/{rid}/notes", headers=primary_headers)
            assert r2.json()["data"]["important_pages"] == d["important_pages"]
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)


# ---------- Toggle / Label endpoints ----------
class TestTogglePage:
    def test_toggle_add_then_remove(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_toggle_add_remove")
        try:
            # add page 5 with label
            r1 = requests.post(
                f"{API}/resources/{rid}/pages/toggle",
                headers=primary_headers,
                json={"page": 5, "label": "intro"},
            )
            assert r1.status_code == 200, r1.text
            d1 = r1.json()["data"]
            assert d1["action"] == "added"
            assert d1["page"] == 5
            assert d1["important_pages"] == [{"page": 5, "label": "intro"}]

            # toggle again -> remove
            r2 = requests.post(
                f"{API}/resources/{rid}/pages/toggle",
                headers=primary_headers,
                json={"page": 5},
            )
            assert r2.status_code == 200
            d2 = r2.json()["data"]
            assert d2["action"] == "removed"
            assert d2["important_pages"] == []

            # GET confirms persistence
            rg = requests.get(f"{API}/resources/{rid}/notes", headers=primary_headers)
            assert rg.json()["data"]["important_pages"] == []
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_toggle_bad_page_zero(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_toggle_bad_zero")
        try:
            r = requests.post(
                f"{API}/resources/{rid}/pages/toggle",
                headers=primary_headers,
                json={"page": 0},
            )
            assert r.status_code == 400
            assert r.json()["error"]["code"] == "bad_page"
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_toggle_bad_page_negative(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_toggle_bad_neg")
        try:
            r = requests.post(
                f"{API}/resources/{rid}/pages/toggle",
                headers=primary_headers,
                json={"page": -2},
            )
            assert r.status_code == 400
            assert r.json()["error"]["code"] == "bad_page"
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)


class TestPageLabel:
    def test_update_label_in_place(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_label_update")
        try:
            # flag page 7 first
            requests.post(
                f"{API}/resources/{rid}/pages/toggle",
                headers=primary_headers,
                json={"page": 7, "label": "old"},
            )
            requests.post(
                f"{API}/resources/{rid}/pages/toggle",
                headers=primary_headers,
                json={"page": 2, "label": "alpha"},
            )
            # update label of 7
            r = requests.post(
                f"{API}/resources/{rid}/pages/label",
                headers=primary_headers,
                json={"page": 7, "label": "main proof"},
            )
            assert r.status_code == 200, r.text
            d = r.json()["data"]
            assert d["page"] == 7
            assert d["label"] == "main proof"
            # important_pages is returned sorted by page
            assert d["important_pages"] == [
                {"page": 2, "label": "alpha"},
                {"page": 7, "label": "main proof"},
            ]
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)

    def test_label_on_non_flagged_page(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_label_not_flagged")
        try:
            r = requests.post(
                f"{API}/resources/{rid}/pages/label",
                headers=primary_headers,
                json={"page": 99, "label": "ghost"},
            )
            assert r.status_code == 400
            assert r.json()["error"]["code"] == "not_flagged"
        finally:
            requests.delete(f"{API}/resources/{rid}", headers=primary_headers)


# ---------- DELETE cascade ----------
class TestDeleteCascade:
    def test_delete_resource_cascades_notes(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        rid = _create_resource(primary_headers, sid, "TEST_cascade_delete")
        # write some notes + important pages
        r0 = requests.post(
            f"{API}/resources/{rid}/notes",
            headers=primary_headers,
            json={"content": "to be deleted", "important_pages": [2, 4]},
        )
        assert r0.status_code == 200

        # delete the resource
        rd = requests.delete(f"{API}/resources/{rid}", headers=primary_headers)
        assert rd.status_code == 200
        assert rd.json()["data"]["deleted"] == 1

        # GET notes returns 404 (resource gone)
        rg = requests.get(f"{API}/resources/{rid}/notes", headers=primary_headers)
        assert rg.status_code == 404
        assert rg.json()["error"]["code"] == "not_found"


# ---------- Phase A regression (no 5xx) ----------
class TestPhaseARegression:
    def test_dashboard(self, primary_headers: Dict[str, str]) -> None:
        r = requests.get(f"{API}/dashboard", headers=primary_headers)
        assert r.status_code == 200
        d = r.json()["data"]
        assert "summary" in d and "subjects" in d

    def test_questions_list_filters(self, primary_headers: Dict[str, str]) -> None:
        r = requests.get(
            f"{API}/questions", headers=primary_headers, params={"limit": 5}
        )
        assert r.status_code == 200
        body = r.json()["data"]
        assert "items" in body and isinstance(body["items"], list)

    def test_create_question_and_flag(
        self, primary_headers: Dict[str, str], subjects: List[Dict[str, Any]]
    ) -> None:
        sid = subjects[0]["subject_id"]
        t = requests.get(f"{API}/subjects/{sid}/topics").json()["data"][0]
        payload = {
            "subject_id": sid,
            "topic_id": t["topic_id"],
            "question_type": "MCQ",
            "question_text": "TEST_phase_a_regression: 2+2?",
            "options": ["3", "4", "5", "6"],
            "correct_answer": "1",
            "solution": "Basic math",
           
        }
        rc = requests.post(f"{API}/questions", headers=primary_headers, json=payload)
        assert rc.status_code == 200, rc.text
        qid = rc.json()["data"]["question_id"]
        try:
            # flag
            rf = requests.post(
                f"{API}/questions/{qid}/flag",
                headers=primary_headers,
                json={"flag_type": "important"},
            )
            assert rf.status_code == 200, rf.text
            assert "important" in rf.json()["data"]["flags"]
        finally:
            requests.delete(f"{API}/questions/{qid}", headers=primary_headers)
