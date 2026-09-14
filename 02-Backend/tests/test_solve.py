import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

def test_solve_returns_provider_and_model():
    with patch.dict(os.environ, {"GROQ_API_KEY": "sk-test"}):
        from app.main import app
        from app.database import init_db
        import uuid

        client = TestClient(app)
        init_db()

        with patch("app.core.router.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "mocked answer"
            mock_response.usage.total_tokens = 5
            mock_client.chat.completions.create.return_value = mock_response
            MockOpenAI.return_value = mock_client

            r = client.post("/auth/register", json={"email": "test@test.com", "password": "test123"})
            assert r.status_code == 200
            login = client.post("/auth/login", json={"email": "test@test.com", "password": "test123"})
            assert login.status_code == 200
            token = login.json()["access_token"]
            user_id = login.json()["user_id"]

            r = client.post("/solve", json={"text": "hello", "user_id": user_id}, headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200
            data = r.json()
            assert "result" in data
            assert "provider" in data
            assert "model" in data
            assert data["provider"] == "groq"
