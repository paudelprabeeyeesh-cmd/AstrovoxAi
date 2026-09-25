"""Comprehensive memory system tests."""

import time
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app import memory as memory_module
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("app.memory.get_user_id_from_token", return_value="user-1"):
        yield


@pytest.fixture
def mock_save_memory():
    with patch("app.memory.save_memory", new_callable=AsyncMock) as m:
        m.return_value = {"id": 1, "user_id": "user-1", "content": "test", "importance": 1, "created_at": "2024-01-01"}
        yield m


@pytest.fixture
def mock_get_user_memory():
    with patch("app.memory.get_user_memory", new_callable=AsyncMock) as m:
        m.return_value = []
        yield m


@pytest.fixture
def mock_get_recent_messages():
    with patch("app.memory.get_recent_messages", new_callable=AsyncMock) as m:
        m.return_value = [
            {"role": "user", "content": "I love Python programming"},
            {"role": "assistant", "content": "Python is great!"},
        ]
        yield m


class TestMemoryEndpoints:
    def test_save_memory_entry(self, mock_save_memory):
        response = client.post(
            "/memory/save",
            headers={"Authorization": "Bearer test"},
            json={"content": "I prefer Python", "importance": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "memory" in data

    def test_save_memory_requires_content(self, mock_save_memory):
        response = client.post(
            "/memory/save",
            headers={"Authorization": "Bearer test"},
            json={"content": "", "importance": 1},
        )
        assert response.status_code == 422

    def test_save_memory_importance_bounds(self, mock_save_memory):
        response = client.post(
            "/memory/save",
            headers={"Authorization": "Bearer test"},
            json={"content": "test", "importance": 0},
        )
        assert response.status_code == 422

        response = client.post(
            "/memory/save",
            headers={"Authorization": "Bearer test"},
            json={"content": "test", "importance": 6},
        )
        assert response.status_code == 422

    def test_get_memory(self, mock_get_user_memory):
        with patch("app.memory.get_user_memory", new_callable=AsyncMock) as m:
            m.return_value = [
                {"id": 1, "content": "fact 1", "importance": 3},
                {"id": 2, "content": "fact 2", "importance": 1},
            ]
            response = client.get("/memory/", headers={"Authorization": "Bearer test"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"
            assert data["count"] == 2

    def test_get_memory_with_limit(self, mock_get_user_memory):
        with patch("app.memory.get_user_memory", new_callable=AsyncMock) as m:
            m.return_value = [{"id": i, "content": f"m{i}", "importance": 1} for i in range(10)]
            response = client.get("/memory/?limit=5", headers={"Authorization": "Bearer test"})
            assert response.status_code == 200

    def test_extract_memory_from_conversation(self, mock_get_recent_messages):
        with patch("app.memory.save_memory", new_callable=AsyncMock) as mock_save:
            response = client.post(
                "/memory/extract-from-conversation",
                headers={"Authorization": "Bearer test"},
                json={"conversation_id": 1},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"

    def test_extract_memory_empty_conversation(self):
        with patch("app.memory.get_recent_messages", new_callable=AsyncMock, return_value=[]):
            response = client.post(
                "/memory/extract-from-conversation",
                headers={"Authorization": "Bearer test"},
                json={"conversation_id": 999},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["extracted"] == []

    def test_memory_requires_auth(self):
        response = client.post("/memory/save", json={"content": "test"})
        assert response.status_code == 401

        response = client.get("/memory/")
        assert response.status_code == 401


class TestMemoryService:
    def test_memory_manager_search(self):
        from app.memory_manager import memory_manager
        with patch.object(memory_manager, "search_memories", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = pytest.run(lambda: memory_manager.search_memories("user-1", "python"))
            mock_search.assert_called_once_with("user-1", "python")

    def test_memory_manager_save(self):
        from app.memory_manager import memory_manager
        with patch.object(memory_manager, "save_memory", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = MagicMock()
            memory_manager.save_memory("user-1", "test content", importance=2)
            mock_save.assert_called_once()

    def test_memory_entry_model(self):
        from app.memory import MemoryEntry
        entry = MemoryEntry(content="Python is great", importance=3)
        assert entry.content == "Python is great"
        assert entry.importance == 3

    def test_memory_entry_validation(self):
        from app.memory import MemoryEntry
        with pytest.raises(Exception):
            MemoryEntry(content="", importance=1)

    def test_memory_response_model(self):
        from app.memory import MemoryResponse
        resp = MemoryResponse(id=1, user_id="user-1", content="test", importance=1, created_at="2024-01-01")
        assert resp.id == 1
        assert resp.content == "test"
