"""Focused contract tests for the streaming chat transport."""

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import chat
from app.main import app


class FakeStreamProvider:
    name = "openai"
    supports_streaming = True
    is_configured = True

    async def stream(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
        yield "Hello"
        yield " world"

    async def stream_with_retry(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
        async for chunk in self.stream(messages, model, temperature, max_tokens, system_prompt):
            yield chunk

    def validate_model(self, model):
        return True

    def sanitize_error(self, error):
        return str(error)


class FakeChatProvider:
    name = "openai"
    supports_streaming = True
    is_configured = True

    async def chat(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
        pass

    def validate_model(self, model):
        return True

    def sanitize_error(self, error):
        return str(error)


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


class MockUsageTracker:
    async def record_success(self, user_id):
        return 1


def _patch_chat(monkeypatch):
    monkeypatch.setattr(chat, "get_user_id_from_token", lambda _header: "user-1")
    monkeypatch.setattr(chat, "get_conversation", _conversation)
    monkeypatch.setattr(chat, "create_message", _create_message)
    monkeypatch.setattr(chat, "get_recent_messages", _recent_messages)
    monkeypatch.setattr(chat, "get_user_memory", _memory)
    monkeypatch.setattr(chat, "update_conversation", _no_op)
    monkeypatch.setattr(chat, "save_memory", _no_op)
    monkeypatch.setattr(chat, "is_valid_model", lambda m: True)
    monkeypatch.setattr(chat, "get_provider_for_model", lambda m: "openai")
    monkeypatch.setattr(chat.ProviderFactory, "get", lambda name: FakeStreamProvider() if name == "openai" else None)
    monkeypatch.setattr(chat, "list_models", lambda: [])
    monkeypatch.setattr(chat, "usage_tracker", MockUsageTracker())


def test_stream_chat_returns_token_events_and_persists_completion(monkeypatch):
    _patch_chat(monkeypatch)

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: metadata' in response.text
    assert 'event: token' in response.text
    assert 'event: done' in response.text
    assert '"content": "Hello"' in response.text
    assert '"content": " world"' in response.text
    assert response.headers.get("X-Event-ID") is not None


def test_stream_chat_rejects_blank_messages(monkeypatch):
    _patch_chat(monkeypatch)

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": ""},
    )

    assert response.status_code == 422


def test_stream_chat_emits_structured_error_event_on_provider_failure(monkeypatch):
    class FailingProvider:
        name = "openai"
        supports_streaming = True
        is_configured = True

        async def stream(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
            raise RuntimeError("Provider down")

        async def stream_with_retry(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
            raise RuntimeError("Provider down")

        def validate_model(self, model):
            return True

        def sanitize_error(self, error):
            return "Provider down"

    monkeypatch.setattr(chat, "get_user_id_from_token", lambda _header: "user-1")
    monkeypatch.setattr(chat, "get_conversation", _conversation)
    monkeypatch.setattr(chat, "create_message", _create_message)
    monkeypatch.setattr(chat, "get_recent_messages", _recent_messages)
    monkeypatch.setattr(chat, "get_user_memory", _memory)
    monkeypatch.setattr(chat, "update_conversation", _no_op)
    monkeypatch.setattr(chat, "save_memory", _no_op)
    monkeypatch.setattr(chat, "is_valid_model", lambda m: True)
    monkeypatch.setattr(chat, "get_provider_for_model", lambda m: "openai")
    monkeypatch.setattr(chat.ProviderFactory, "get", lambda name: FailingProvider() if name == "openai" else None)
    monkeypatch.setattr(chat, "list_models", lambda: [])
    monkeypatch.setattr(chat, "usage_tracker", MockUsageTracker())

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert 'event: metadata' in response.text
    assert 'event: error' in response.text
    assert 'Provider down' in response.text
    assert '"code": "PROVIDER_ERROR"' in response.text
    assert '"retry_after_ms"' in response.text


def test_stream_chat_keepalive_header(monkeypatch):
    _patch_chat(monkeypatch)

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-cache"
    assert response.headers.get("X-Accel-Buffering") == "no"


def test_stream_chat_supports_last_event_id_header(monkeypatch):
    _patch_chat(monkeypatch)

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test", "Last-Event-ID": "prev-event-123"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-Event-ID") is not None


def test_stream_chat_emits_fallback_event_on_secondary_provider(monkeypatch):
    class FailingThenSucceedingProvider:
        name = "openai"
        supports_streaming = True
        is_configured = True
        call_count = 0

        async def stream(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
            self.call_count += 1
            if self.call_count == 1:
                raise RuntimeError("Primary down")
            yield "Recovered"

        async def stream_with_retry(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
            async for chunk in self.stream(messages, model, temperature, max_tokens, system_prompt):
                yield chunk

        def validate_model(self, model):
            return True

        def sanitize_error(self, error):
            return str(error)

    class FallbackProvider:
        name = "anthropic"
        supports_streaming = True
        is_configured = True

        async def stream(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
            yield "Fallback result"

        async def stream_with_retry(self, messages, model, temperature=0.7, max_tokens=2000, system_prompt=None):
            async for chunk in self.stream(messages, model, temperature, max_tokens, system_prompt):
                yield chunk

        def validate_model(self, model):
            return True

        def sanitize_error(self, error):
            return str(error)

    monkeypatch.setattr(chat, "get_user_id_from_token", lambda _header: "user-1")
    monkeypatch.setattr(chat, "get_conversation", _conversation)
    monkeypatch.setattr(chat, "create_message", _create_message)
    monkeypatch.setattr(chat, "get_recent_messages", _recent_messages)
    monkeypatch.setattr(chat, "get_user_memory", _memory)
    monkeypatch.setattr(chat, "update_conversation", _no_op)
    monkeypatch.setattr(chat, "save_memory", _no_op)
    monkeypatch.setattr(chat, "is_valid_model", lambda m: True)
    monkeypatch.setattr(chat, "get_provider_for_model", lambda m: "openai")

    def _get_fallback(name):
        if name == "anthropic":
            return FallbackProvider()
        return FailingThenSucceedingProvider()

    monkeypatch.setattr(chat.ProviderFactory, "get", _get_fallback)
    monkeypatch.setattr(chat, "list_models", lambda: [])
    monkeypatch.setattr(chat, "usage_tracker", MockUsageTracker())

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert 'event: fallback' in response.text
    assert 'event: token' in response.text
    assert 'event: done' in response.text


def test_stream_chat_message_endpoint_streams_when_requested(monkeypatch):
    _patch_chat(monkeypatch)

    response = TestClient(app).post(
        "/chat/message",
        headers={"Authorization": "Bearer test"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model", "stream": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: metadata' in response.text
    assert 'event: token' in response.text
    assert 'event: done' in response.text


def test_stream_chat_metadata_event_contains_resumed_flag(monkeypatch):
    _patch_chat(monkeypatch)

    response = TestClient(app).post(
        "/chat/stream",
        headers={"Authorization": "Bearer test", "Last-Event-ID": "some-prev-id"},
        json={"conversation_id": 7, "message": "Hello", "model": "test-model"},
    )

    assert response.status_code == 200
    assert '"resumed": true' in response.text
    assert '"event_id"' in response.text
    assert '"provider"' in response.text
    assert '"model"' in response.text
