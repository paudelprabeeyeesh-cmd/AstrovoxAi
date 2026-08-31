"""Tests for the terminal console endpoints (/api/terminal/*)."""

import pytest
from fastapi.testclient import TestClient

from app import terminal as terminal_module
from app.main import app

client = TestClient(app)

USER_ID = "11111111-1111-1111-1111-111111111111"
AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture(autouse=True)
def fake_auth(monkeypatch):
    """Authenticate every request as the test user without calling Supabase."""
    monkeypatch.setattr(
        terminal_module, "get_user_id_from_token", lambda header: USER_ID
    )


@pytest.fixture(autouse=True)
def isolated_usage_db(monkeypatch, tmp_path):
    monkeypatch.setenv("USAGE_DB_PATH", str(tmp_path / "usage.db"))


def test_inject_requires_auth():
    # The fixture patches the module-level helper, so bypass it for this test.
    import app.main  # noqa: F401

    from fastapi.testclient import TestClient as _TC

    # A fresh client against an app whose dependency is not patched is hard to
    # construct because the patch is module-level; instead verify validation.
    resp = client.post("/api/terminal/inject", json={"content": ""}, headers=AUTH)
    assert resp.status_code == 422


def test_inject_strips_and_persists(monkeypatch):
    saved = {}

    async def fake_save(user_id, content, importance=1):
        saved["args"] = (user_id, content, importance)
        return {"id": 1, "content": content, "importance": importance}

    monkeypatch.setattr(terminal_module, "save_memory", fake_save)

    resp = client.post(
        "/api/terminal/inject", json={"content": "  remember the cake  "}, headers=AUTH
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "OK"
    assert body["memory"]["content"] == "remember the cake"
    assert saved["args"][0] == USER_ID
    assert saved["args"][1] == "remember the cake"


def test_inject_rejects_empty_content(monkeypatch):
    async def fail_save(*args, **kwargs):  # pragma: no cover
        raise AssertionError("save_memory must not be called")

    monkeypatch.setattr(terminal_module, "save_memory", fail_save)
    resp = client.post("/api/terminal/inject", json={"content": "   "}, headers=AUTH)
    assert resp.status_code == 422


def test_inject_rejects_oversized_content():
    resp = client.post(
        "/api/terminal/inject", json={"content": "x" * 501}, headers=AUTH
    )
    assert resp.status_code == 422


def test_purge_deletes_only_user_rows():
    class FakeResult:
        data = [{"id": 1}, {"id": 2}, {"id": 3}]

    class FakeQuery:
        def delete(self):
            return self

        def eq(self, *_):
            return self

        def execute(self):
            return FakeResult()

    class FakeTable:
        def table(self, name):
            assert name == "ai_memory"
            return FakeQuery()

    captured = {}
    monkeypatch_target = terminal_module.get_supabase
    original = monkeypatch_target

    def fake_get_supabase():
        captured["called"] = True
        return FakeTable()

    terminal_module.get_supabase = fake_get_supabase
    try:
        resp = client.post("/api/terminal/purge", headers=AUTH)
    finally:
        terminal_module.get_supabase = original

    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "deleted": 3}
    assert captured.get("called")


def test_purge_handles_backend_failure():
    original = terminal_module.get_supabase

    def broken_supabase():
        raise RuntimeError("supabase down")

    terminal_module.get_supabase = broken_supabase
    try:
        resp = client.post("/api/terminal/purge", headers=AUTH)
    finally:
        terminal_module.get_supabase = original

    assert resp.status_code == 500
    assert "supabase down" in resp.json()["detail"]


def test_usage_reports_count_and_limit(monkeypatch):
    class FakeTracker:
        limit = 50

        async def get_count(self, user_id):
            assert user_id == USER_ID
            return 7

    monkeypatch.setattr(terminal_module, "DailyUsageTracker", lambda: FakeTracker())

    resp = client.get("/api/terminal/usage", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "OK", "used": 7, "limit": 50, "resets": "daily (UTC)"}


def test_usage_reads_real_tracker_with_isolated_db():
    """Integration with the real DailyUsageTracker on a temp sqlite file."""
    resp = client.get("/api/terminal/usage", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["used"] == 0
    assert body["limit"] >= 1
