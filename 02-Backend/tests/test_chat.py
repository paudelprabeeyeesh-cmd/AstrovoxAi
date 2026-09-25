"""Comprehensive chat endpoint tests."""

import time
import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from types import SimpleNamespace

from app import chat
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_auth():
    with patch("app.chat.get_user_id_from_token", return_value="user-1") as m:
        yield m


@pytest.fixture
def mock_db():
    with patch("app.chat.create_conversation", new_callable=AsyncMock) as m:
        m.return_value = {"id": 1, "title": "Test", "user_id": "user-1", "model": "gpt-4"}
        yield m


@pytest.fixture
def fake_completions():
    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["stream"] is True
            return iter([
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello"))], usage=None),
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" world"))], usage=SimpleNamespace(total_tokens=12)),
            ])

    return FakeCompletions()


class TestChatConversations:
    def test_create_conversation(self, mock_auth, mock_db):
        response = client.post(
            "/chat/conversations",
            headers={"Authorization": "Bearer test"},
            json={"title": "New Chat", "model": "gpt-4"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "conversation" in data

    def test_create_conversation_requires_auth(self):
        response = client.post("/chat/conversations", json={"title": "No Auth"})
        assert response.status_code == 401

    def test_get_conversations(self, mock_auth):
        with patch("app.chat.get_conversations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [{"id": 1, "title": "Chat 1"}]
            response = client.get("/chat/conversations", headers={"Authorization": "Bearer test"})
            assert response.status_code == 200
            data = response.json()
            assert "conversations" in data

    def test_get_conversation_by_id(self, mock_auth):
        with patch("app.chat.get_conversation", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": 1, "title": "Chat 1"}
            response = client.get("/chat/conversations/1", headers={"Authorization": "Bearer test"})
            assert response.status_code == 200

    def test_delete_conversation(self, mock_auth):
        with patch("app.chat.delete_conversation", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = True
            response = client.delete("/chat/conversations/1", headers={"Authorization": "Bearer test"})
            assert response.status_code in (200, 204)


class TestChatMessages:
    def test_send_message(self, mock_auth):
        with patch("app.chat.is_valid_model", return_value=True), \
             patch("app.chat.create_conversation", new_callable=AsyncMock, return_value={"id": 1}), \
             patch("app.chat.create_message", new_callable=AsyncMock, return_value={"id": 1, "role": "user", "content": "Hi"}), \
             patch("app.chat.get_recent_messages", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.update_conversation", new_callable=AsyncMock), \
             patch("app.chat.save_memory", new_callable=AsyncMock), \
             patch("app.chat.client") as mock_client:
            mock_client.chat.completions.create.return_value = iter([
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hi"))], usage=SimpleNamespace(total_tokens=5)),
            ])
            response = client.post(
                "/chat/send",
                headers={"Authorization": "Bearer test"},
                json={"conversation_id": 1, "message": "Hello", "model": "gpt-4"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data or "response" in data

    def test_send_message_blank_rejected(self, mock_auth):
        response = client.post(
            "/chat/send",
            headers={"Authorization": "Bearer test"},
            json={"conversation_id": 1, "message": "   ", "model": "gpt-4"},
        )
        assert response.status_code == 422

    def test_send_message_invalid_model(self, mock_auth):
        with patch("app.chat.is_valid_model", return_value=False):
            response = client.post(
                "/chat/send",
                headers={"Authorization": "Bearer test"},
                json={"conversation_id": 1, "message": "Hello", "model": "bad-model"},
            )
            assert response.status_code == 422


class TestChatStream:
    def test_stream_returns_events(self, mock_auth, fake_completions):
        with patch("app.chat.get_conversation", new_callable=AsyncMock, return_value={"id": 1}), \
             patch("app.chat.create_message", new_callable=AsyncMock), \
             patch("app.chat.get_recent_messages", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.update_conversation", new_callable=AsyncMock), \
             patch("app.chat.save_memory", new_callable=AsyncMock), \
             patch("app.chat.client") as mock_client:
            mock_client.chat.completions.create.side_effect = fake_completions.create
            response = client.post(
                "/chat/stream",
                headers={"Authorization": "Bearer test"},
                json={"conversation_id": 1, "message": "Hello", "model": "gpt-4"},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            assert "Hello" in response.text

    def test_stream_rejects_blank_messages(self, mock_auth):
        response = client.post(
            "/chat/stream",
            headers={"Authorization": "Bearer test"},
            json={"conversation_id": 1, "message": "   "},
        )
        assert response.status_code == 422

    def test_stream_requires_conversation_id(self, mock_auth):
        response = client.post(
            "/chat/stream",
            headers={"Authorization": "Bearer test"},
            json={"message": "Hello"},
        )
        assert response.status_code == 422

    def test_stream_message_too_long(self, mock_auth):
        response = client.post(
            "/chat/stream",
            headers={"Authorization": "Bearer test"},
            json={"conversation_id": 1, "message": "x" * 5000, "model": "gpt-4"},
        )
        assert response.status_code == 422


class TestChatModels:
    def test_get_models(self, mock_auth):
        with patch("app.chat.get_provider_for_model", return_value="openai"), \
             patch("app.chat.get_model_info", return_value=MagicMock(id="gpt-4", name="GPT-4")):
            response = client.get("/chat/models", headers={"Authorization": "Bearer test"})
            assert response.status_code == 200
            data = response.json()
            assert "models" in data

    def test_invalid_model_rejected_on_send(self, mock_auth):
        with patch("app.chat.is_valid_model", return_value=False):
            response = client.post(
                "/chat/send",
                headers={"Authorization": "Bearer test"},
                json={"conversation_id": 1, "message": "Hello", "model": "fake-model-xyz"},
            )
            assert response.status_code == 422
