import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

def test_solve_returns_provider_and_model():
    from app.database import init_db
    import app.main as main_module

    init_db()

    with patch("app.core.router.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "mocked answer"
        mock_response.usage.total_tokens = 5
        mock_client.chat.completions.create.return_value = mock_response
        MockOpenAI.return_value = mock_client

        with patch.object(main_module.llm_client, "call_llm", return_value={
            "text": "mocked answer",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "tokens": 5,
        }):
            client = TestClient(main_module.app)
            email = f"solve-test-{int(time.time())}@test.com"
            r = client.post("/auth/register", json={"email": email, "password": "test123"})
            assert r.status_code == 200, r.text
            from app.database import get_db
            with get_db() as conn:
                conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
                conn.commit()
            login = client.post("/auth/login", json={"email": email, "password": "test123"})
            assert login.status_code == 200
            token = login.json()["access_token"]
            user_id = login.json()["user_id"]

            r = client.post("/solve", json={"text": "hello", "user_id": user_id}, headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert "result" in data
            assert "provider" in data
            assert "model" in data
            assert data["provider"] == "groq"
