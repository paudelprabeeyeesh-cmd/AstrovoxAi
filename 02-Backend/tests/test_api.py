import time
import uuid
import importlib
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.database import init_db, get_db

client = TestClient(importlib.import_module("app.main").app)


def _register():
    email = f"api-{int(time.time())}-{uuid.uuid4().hex[:6]}@test.com"
    r = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200, r.text
    with get_db() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
        conn.commit()
    r = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"], r.json()["user_id"]


def test_solve_endpoint():
    init_db()
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.main.llm_client.call_llm", return_value={
        "text": "Mocked answer",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "tokens": 10,
        "confidence": 0.9,
    }):
        with patch("app.routers.solve.ground_answer", return_value=("Mocked answer", False, 0.9)):
            with patch("app.core.suggestions.SuggestionEngine") as MockSuggestion:
                MockSuggestion.return_value.generate.return_value = []
                r = client.post("/solve", json={"text": "Hello", "user_id": user_id}, headers=headers)
                assert r.status_code == 200, r.text
                data = r.json()
                assert data["result"] == "Mocked answer"
                assert data["provider"] == "groq"
                assert data["model"] == "llama-3.3-70b-versatile"
                assert data["cost_usd"] >= 0
                assert "conversation_id" in data
                assert "message_id" in data
                assert data["confidence"] == 0.9
                assert data["refused"] is False


def test_streaming_endpoint():
    init_db()
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}

    async def _fake_stream(prompt, system="", timeout=30):
        yield {"token": "Hello", "provider": "groq", "model": "llama-3.3-70b-versatile"}
        yield {"token": " world", "provider": "groq", "model": "llama-3.3-70b-versatile"}

    with patch("app.main.llm_client.stream_llm", side_effect=lambda *args, **kwargs: _fake_stream(kwargs.get("prompt", ""))):
        with patch("app.routers.solve.ground_answer", return_value=("Hello world", False, 0.9)):
            with patch("app.core.suggestions.SuggestionEngine") as MockSuggestion:
                MockSuggestion.return_value.generate.return_value = []
                r = client.post("/solve/stream", json={"text": "Hello", "user_id": user_id}, headers=headers)
                assert r.status_code == 200, r.text
                assert r.headers["content-type"] == "text/event-stream; charset=utf-8"
                text = r.text
                assert "data: " in text
                assert "Hello" in text
                assert "world" in text
                assert "[DONE]" in text


def test_usage_tracking():
    init_db()
    token, user_id = _register()
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.main.llm_client.call_llm", return_value={
        "text": "Mocked answer",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "tokens": 10,
        "confidence": 0.9,
    }):
        with patch("app.routers.solve.ground_answer", return_value=("Mocked answer", False, 0.9)):
            with patch("app.core.suggestions.SuggestionEngine") as MockSuggestion:
                MockSuggestion.return_value.generate.return_value = []
                r = client.post("/solve", json={"text": "Track usage", "user_id": user_id}, headers=headers)
                assert r.status_code == 200, r.text
    with patch("app.usage.get_db") as mock_get_db:
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.fetchone.return_value = {"c": 1}
        from app.usage import record_usage
        record_usage(user_id, 10, 0.0001, "llama-3.3-70b-versatile", False)
        inserts = [call for call in mock_conn.execute.call_args_list if "INSERT INTO usage" in call[0][0]]
        assert len(inserts) >= 1
