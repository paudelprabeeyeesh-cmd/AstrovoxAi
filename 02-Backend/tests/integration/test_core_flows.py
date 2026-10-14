import importlib
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from fastapi.testclient import TestClient

client = TestClient(importlib.import_module("app.main").app)

from app.auth import get_current_user
from app.utils.auth.auth_utils import get_user_id_from_token


def _mock_user():
    return {"user_id": "test-user", "email": "test@test.com"}


def _mock_user_id():
    return "test-user"


def _fake_provider(content="Hi there", tokens=10):
    """A provider double matching app.providers.base.AIProvider.

    app.chat resolves its LLM through ProviderFactory.get(...) and calls
    `chat_with_retry`, not a raw SDK client, so the double must expose that
    interface to be a faithful stand-in.
    """
    provider = MagicMock()
    provider.is_configured = True
    provider.supports_streaming = False
    provider.sanitize_error = lambda exc: str(exc)
    response = MagicMock()
    response.content = content
    response.tokens_used = tokens
    response.input_tokens = tokens
    response.output_tokens = tokens
    provider.chat_with_retry = AsyncMock(return_value=response)
    return provider


def _fake_session(session_id="session-1", goal="test", status="completed", result="done"):
    """A CollaborationSession double that matches the real model's types.

    The real session carries `TaskStatus` enums for `status`, not plain
    strings, because the route serialises them with `.value`. A string mock
    makes the route raise AttributeError, which is a defect in the test,
    not in the route.
    """
    from app.multi_agent import TaskStatus

    session = MagicMock()
    session.id = session_id
    session.goal = goal
    session.result = result
    session.status = TaskStatus(status) if isinstance(status, str) else status
    session.tasks = []
    session.messages = []
    return session


def _fake_supabase():
    """A Supabase double for the repository layer.

    `get_supabase` is `lru_cache`d, so its `.return_value` cannot be patched.
    Two call paths are covered: the shared helper resolves the accessor at
    call time (`app.utils.auth.auth_utils.get_supabase`), while
    `app.repositories.database.client` and several other modules bind the
    client once at import time, so their module globals are replaced too.
    Otherwise one path keeps the import-time client and authenticates
    against a real server.
    """
    fake = MagicMock()
    fake.auth.get_user.return_value = MagicMock(
        user=MagicMock(id="test-user", email="test@test.com")
    )
    fake.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
    fake.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
    fake.table.return_value.update.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
    fake.table.return_value.delete.return_value.execute.return_value = MagicMock(data=[])
    return fake


def _fake_usage_tracker():
    """A DailyUsageTracker double that never exhausts its quota.

    The real tracker persists a daily counter in a database shared by the
    whole session, so after enough chat requests it raises
    UsageQuotaExceeded and `/chat/message` answers 429. That is a quota
    decision, not the behaviour these flows are testing, and it makes them
    fail depending on how many earlier requests ran in the same session.
    """
    tracker = MagicMock()
    tracker.record_success = AsyncMock(return_value=None)
    return tracker




@pytest.fixture(autouse=True)
def _mock_auth():
    app = importlib.import_module("app.main").app
    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_user_id_from_token] = _mock_user_id
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_user_id_from_token, None)


@pytest.fixture(autouse=True)
def _mock_external():
    patches = [
        patch("app.chat.ProviderFactory.get", return_value=_fake_provider()),
        patch("app.chat.usage_tracker", _fake_usage_tracker()),
        patch("app.chat.is_valid_model", return_value=True),
        patch("app.chat.get_model_info", return_value=MagicMock(id="gpt-4", name="GPT-4")),
        patch("app.chat.get_provider_for_model", return_value="openai"),
        patch("app.services.vector.embeddings_route.embedding_service", MagicMock()),
        patch("app.memory_engine.engine.EmbeddingService.embed_text", new_callable=AsyncMock, return_value=MagicMock(vector=[0.1] * 1536)),
        patch("app.rag.embeddings.EmbeddingGenerator.embed", return_value=MagicMock(embedding=[0.1] * 1536, model="test", dimensions=1536)),
        patch("app.rag.retrieval.MultiQueryRetriever.retrieve", return_value=[]),
        patch("app.rag.compression.ContextCompressor.compress", return_value="compressed context"),
        patch("app.utils.auth.auth_utils.get_supabase", return_value=_fake_supabase()),
        # Three modules bind the client once at import time
        # (`supabase = get_supabase()`), so patching the accessor is too late
        # for them: their module global has to be replaced directly. Without
        # this they keep the import-time client and authenticate against it.
        patch("app.auth.supabase", _fake_supabase()),
        patch("app.core_assistant.supabase", _fake_supabase()),
        patch("app.telemetry.supabase", _fake_supabase()),
        patch("app.repositories.database.client.supabase", _fake_supabase()),
        patch("app.services.memory.memory_enhanced.memory_store.add_memory", return_value=MagicMock(id="mem-1", content="test", memory_type="general", importance=1)),
        patch("app.services.memory.memory_enhanced.memory_store.search", return_value=[]),
        patch("app.services.memory.memory_enhanced.memory_store.get_episodic", return_value=[]),
        patch("app.services.memory.memory_enhanced.memory_store.get_semantic", return_value=[]),
        patch("app.services.memory.memory_enhanced.memory_store.get_stats", return_value={"total": 0}),
        patch("app.api.v1.tool_executor.registry.list_tools", return_value=[{"name": "calculator", "description": "Calc", "sync": True}]),
        patch("app.multi_agent.collaboration_manager.create_session", return_value=_fake_session()),
        patch("app.multi_agent.collaboration_manager.run_session", new_callable=AsyncMock, return_value=_fake_session(status="completed", result="done")),
        patch("app.multi_agent.collaboration_manager.get_session", return_value=_fake_session(status="completed", result="done")),
        patch("app.multi_agent.collaboration_manager.get_user_sessions", return_value=[]),
        patch("app.vector.engine.search_engine.index"),
        patch("app.vector.engine.search_engine.search", return_value=MagicMock(results=[])),
        patch("app.vector.engine.search_engine.remove", return_value=True),
        patch("app.vector.engine.search_engine.get_stats", return_value={"document_count": 0}),
        patch("app.main.llm_client.call_llm", return_value={"text": "Mocked answer", "provider": "test", "model": "test-model", "tokens": 10, "confidence": 0.9}),
        patch("app.main.llm_client.stream_llm", return_value=iter([{"token": "Mocked", "provider": "test", "model": "test-model"}])),
        patch("app.billing.stripe", MagicMock()),
        patch("app.billing._STRIPE_CONFIGURED", True),
        patch("openai.OpenAI", return_value=MagicMock()),
    ]
    from contextlib import ExitStack

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


class TestUserToChat:
    def test_user_can_create_conversation(self):
        response = client.post(
            "/chat/conversations",
            headers={"Authorization": "Bearer test-token"},
            json={"title": "Test Chat", "model": "gpt-4"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "conversation" in data

    def test_user_can_list_conversations(self):
        response = client.get(
            "/chat/conversations",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "conversations" in data

    def test_user_can_send_message(self):
        with patch("app.chat.create_conversation", new_callable=AsyncMock, return_value={"id": 1, "title": "Test", "user_id": "test-user", "model": "gpt-4"}), \
             patch("app.chat.create_message", new_callable=AsyncMock, return_value={"id": 1, "role": "user", "content": "Hello"}), \
             patch("app.chat.get_recent_messages", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.update_conversation", new_callable=AsyncMock), \
             patch("app.chat.save_memory", new_callable=AsyncMock), \
             patch("app.chat.ProviderFactory.get", return_value=_fake_provider("Hi there")):
            response = client.post(
                "/chat/message",
                headers={"Authorization": "Bearer test-token"},
                json={"conversation_id": 1, "message": "Hello", "model": "gpt-4"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"
            assert "user_message" in data
            assert "ai_message" in data


class TestChatToMemory:
    def test_chat_saves_memory(self):
        with patch("app.chat.create_conversation", new_callable=AsyncMock, return_value={"id": 1, "title": "Test", "user_id": "test-user", "model": "gpt-4"}), \
             patch("app.chat.create_message", new_callable=AsyncMock, return_value={"id": 1, "role": "user", "content": "Remember this"}), \
             patch("app.chat.get_recent_messages", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.update_conversation", new_callable=AsyncMock), \
             patch("app.chat.save_memory", new_callable=AsyncMock) as mock_save_memory, \
             patch("app.chat.ProviderFactory.get", return_value=_fake_provider("I will remember that")):
            response = client.post(
                "/chat/message",
                headers={"Authorization": "Bearer test-token"},
                json={"conversation_id": 1, "message": "Remember this", "model": "gpt-4"},
            )
            assert response.status_code == 200

    def test_memory_can_be_stored_and_recalled(self):
        response = client.post(
            "/api/memory-v2/remember",
            headers={"Authorization": "Bearer test-token"},
            json={"content": "User likes pizza", "importance": 3, "category": "personal"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "memory" in data

        response = client.post(
            "/api/memory-v2/recall",
            headers={"Authorization": "Bearer test-token"},
            json={"query": "pizza", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "results" in data


class TestMemoryToRAG:
    def test_memory_context_used_in_rag(self):
        with patch("app.rag.embeddings.EmbeddingGenerator.embed", return_value=MagicMock(embedding=[0.1] * 1536, model="test", dimensions=1536)):
            response = client.post(
                "/rag/search",
                headers={"Authorization": "Bearer test-token"},
                json={"query": "test query", "top_k": 5},
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_rag_document_list(self):
        response = client.get(
            "/rag/documents",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestRAGToLLM:
    def test_rag_provides_context_for_llm(self):
        with patch("app.chat.create_conversation", new_callable=AsyncMock, return_value={"id": 1, "title": "Test", "user_id": "test-user", "model": "gpt-4"}), \
             patch("app.chat.create_message", new_callable=AsyncMock, return_value={"id": 1, "role": "user", "content": "What is in my docs?"}), \
             patch("app.chat.get_recent_messages", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.get_user_memory", new_callable=AsyncMock, return_value=[]), \
             patch("app.chat.update_conversation", new_callable=AsyncMock), \
             patch("app.chat.save_memory", new_callable=AsyncMock), \
             patch("app.chat.ProviderFactory.get", return_value=_fake_provider("Based on your docs")), \
             patch("app.rag.retrieval.MultiQueryRetriever.retrieve", return_value=[
                 MagicMock(chunk_id="c1", document_id="d1", content="doc content", score=0.9, source="dense")
             ]):
            response = client.post(
                "/chat/message",
                headers={"Authorization": "Bearer test-token"},
                json={"conversation_id": 1, "message": "What is in my docs?", "model": "gpt-4"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"


class TestToolToAgent:
    def test_tools_are_listed(self):
        response = client.get(
            "/api/v1/tools",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert any(t["name"] == "calculator" for t in data["tools"])

    def test_tool_can_be_executed(self):
        response = client.post(
            "/api/v1/tools/calculator/execute",
            headers={"Authorization": "Bearer test-token"},
            json={"expression": "2+2"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["success"] is True
        assert data["result"] == "4"

    def test_agent_can_be_created_and_run(self):
        response = client.post(
            "/agents/sessions",
            headers={"Authorization": "Bearer test-token"},
            json={"goal": "Build a web app"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "session" in data
        session_id = data["session"]["id"]

        response = client.post(
            f"/agents/sessions/{session_id}/run",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["session"]["status"] == "completed"


class TestAgentToDatabase:
    def test_agent_session_persists(self):
        response = client.post(
            "/agents/sessions",
            headers={"Authorization": "Bearer test-token"},
            json={"goal": "Persist data"},
        )
        assert response.status_code == 200
        session_id = response.json()["session"]["id"]

        response = client.get(
            f"/agents/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["session"]["id"] == session_id

    def test_user_sessions_listed(self):
        response = client.get(
            "/agents/sessions",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "sessions" in data


class TestAuthenticationToProtectedAPI:
    def test_protected_endpoint_requires_auth(self):
        response = client.get("/chat/conversations")
        assert response.status_code == 401

    def test_protected_endpoint_accepts_valid_token(self):
        response = client.get(
            "/chat/conversations",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200

    def test_auth_me_endpoint(self):
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "user" in data

    def test_agent_routes_require_auth(self):
        response = client.post("/agents/sessions", json={"goal": "test"})
        assert response.status_code == 401

        response = client.get("/agents/sessions")
        assert response.status_code == 401
