"""Request-validation tests.

Pydantic validates the request body before the route handler runs (and before
any auth/Supabase calls), so these assert 422s without needing credentials.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_send_message_rejects_empty_message():
    resp = client.post(
        "/chat/message",
        json={"conversation_id": 1, "message": ""},
    )
    assert resp.status_code == 422


def test_send_message_rejects_oversized_message():
    resp = client.post(
        "/chat/message",
        json={"conversation_id": 1, "message": "x" * 8001},
    )
    assert resp.status_code == 422


def test_save_memory_rejects_empty_content():
    resp = client.post("/memory/save", json={"content": "", "importance": 1})
    assert resp.status_code == 422


def test_save_memory_rejects_out_of_range_importance():
    resp = client.post("/memory/save", json={"content": "hi", "importance": 99})
    assert resp.status_code == 422
