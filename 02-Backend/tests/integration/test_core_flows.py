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
        patch("app.chat.client", MagicMock()),
        patch("app.chat.is_valid_model", return_value=True),
        patch("app.chat.get_model_info", return_value=MagicMock(id="gpt-4", name="GPT-4")),
        patch("app.chat.get_provider_for_model", return_value="openai"),
        patch("app.services.vector.embeddings_route.embedding_service", MagicMock()),
        patch("app.memory_engine.engine.EmbeddingService.embed_text", new_callable=AsyncMock, return_value=MagicMock(vector=[0.1] * 1536)),
        patch("app.rag.embeddings.EmbeddingGenerator.embed", return_value=MagicMock(embedding=[0.1] * 1536, model="test", dimensions=1536)),
        patch("app.rag.retrieval.MultiQueryRetriever.retrieve", return_value=[]),
        patch("app.rag.compression.ContextCompressor.compress", return_value="compressed context"),
        patch("app.repositories.database.supabase_client.get_supabase.return_value.auth.get_user", return_value=MagicMock(user=MagicMock(id="test-user", email="test@test.com"))),
        patch("app.repositories.database.supabase_client.get_supabase.return_value.table.return_value.insert.return_value.execute", return_value=MagicMock(data=[{"id": 1}])),
        patch("app.repositories.database.supabase_client.get_supabase.return_value.table.return_value.select.return_value.execute", return_value=MagicMock(data=[])),
        patch("app.repositories.database.supabase_client.get_supabase.return_value.table.return_value.update.return_value.execute", return_value=MagicMock(data=[{"id": 1}])),
        patch("app.repositories.database.supabase_client.get_supabase.return_value.table.return_value.delete.return_value.execute", return_value=MagicMock(data=[])),
        patch("app.services.memory.memory_enhanced.memory_store.add_memory", return_value=MagicMock(id="mem-1", content="test", memory_type="general", importance=1)),
        patch("app.services.memory.memory_enhanced.memory_store.search", return_value=[]),
        patch("app.services.memory.memory_enhanced.memory_store.get_episodic", return_value=[]),
        patch("app.services.memory.memory_enhanced.memory_store.get_semantic", return_value=[]),
        patch("app.services.memory.memory_enhanced.memory_store.get_stats", return_value={"total": 0}),
        patch("app.tools.tool_registry.get_tools", return_value=[{"name": "calculator", "description": "Calc", "sync": True}]),
        patch("app.tools.tool_registry.execute", return_value=MagicMock(success=True, result="4", tool_name="calculator", metadata={})),
        patch("app.multi_agent.collaboration_manager.create_session", return_value=MagicMock(id="session-1", goal="test", status="pending", tasks=[], messages=[])),
        patch("app.multi_agent.collaboration_manager.run_session", new_callable=AsyncMock, return_value=MagicMock(id="session-1", goal="test", status="completed", result="done", tasks=[], messages=[])),
        patch("app.multi_agent.collaboration_manager.get_session", return_value=MagicMock(id="session-1", goal="test", status="completed", result="done")),
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
    with pytest.MonkeyPatch.context() as mp:
        for p in patches:
            mp.setattr(p.target, p.attribute, p.new if hasattr(p, 'new') else MagicMock())
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
             patch("app.chat.client") as mock_client:
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(delta=MagicMock(content="Hi there"), finish_reason="stop")],
                usage=MagicMock(total_tokens=10),
            )
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
             patch("app.chat.client") as mock_client:
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(delta=MagicMock(content="I will remember that"), finish_reason="stop")],
                usage=MagicMock(total_tokens=10),
            )
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
             patch("app.chat.client") as mock_client, \
             patch("app.rag.retrieval.MultiQueryRetriever.retrieve", return_value=[
                 MagicMock(chunk_id="c1", document_id="d1", content="doc content", score=0.9, source="dense")
             ]):
            mock_client.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(delta=MagicMock(content="Based on your docs"), finish_reason="stop")],
                usage=MagicMock(total_tokens=15),
            )
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
            "/realtime/tools/",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "tools" in data

    def test_tool_can_be_executed(self):
        response = client.post(
            "/realtime/tools/execute",
            headers={"Authorization": "Bearer test-token"},
            json={"tool_name": "calculator", "parameters": {"expression": "2+2"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["tool"] == "calculator"

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
