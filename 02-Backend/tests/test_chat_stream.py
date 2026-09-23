"""Focused contract tests for the streaming chat transport."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import chat
from app.main import app


class FakeCompletions:
    def create(self, **kwargs):
        assert kwargs["stream"] is True
        assert kwargs["messages"][-1] == {"role": "user", "content": "Hello"}
        return iter(
            [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello"))],
                    usage=None,
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=" world"))],
                    usage=SimpleNamespace(total_tokens=12),
                ),
            ]
        )


class FakeClient:
    chat = SimpleNamespace(completions=FakeCompletions())


async def _conversation(*_args, **_kwargs):
    return {"id": 7}


async def _create_message(*args, **kwargs):
    return {"id": 11, "role": args[2], "content": args[3]}


async def _recent_messages(*_args, **_kwargs):
    return [{"role": "user", "content": "Hello"}]


async def _memory(*_args, **_kwargs):
    return []


async def _no_op(*_args, **_kwargs):
    return None


def test_stream_chat_returns_token_events_and_persists_completion(monkeypatch):
    monkeypatch.setattr(chat, "get_user_id_from_token", lambda _header: "user-1")
    monkeypatch.setattr(chat, "get_conversation", _conversation)
    monkeypatch.setattr(chat, "create_message", _create_message)
    monkeypatch.setattr(chat, "get_recent_messages", _recent_messages)
    monkeypatch.setattr(chat, "get_user_memory", _memory)
    monkeypatch.setattr(chat, "update_conversation", _no_op)
    monkeypatch.setattr(chat, "save_memory", _no_op)
    monkeypatch.setattr(chat, "client", FakeClient())

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: token\ndata: {"content": "Hello"}' in response.text
    assert 'event: token\ndata: {"content": " world"}' in response.text
    assert 'event: done\ndata: ' in response.text
    assert '"tokens_used": 12' in response.text


def test_stream_chat_rejects_blank_messages():
    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": ""},
    )

    assert response.status_code == 422
