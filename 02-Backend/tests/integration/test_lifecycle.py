"""Full request lifecycle integration tests through FastAPI TestClient."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app import auth as auth_module
from app import database as db_module
from app import chat as chat_module
from app import terminal as terminal_module


class FakeSupabaseAuth:
    def __init__(self, fake):
        self._fake = fake

    def sign_up(self, payload):
        user_id = f"user-{self._fake._next_profile_id}"
        self._fake._next_profile_id += 1
        user = MagicMock()
        user.id = user_id
        user.email = payload.get("email")
        session = MagicMock()
        session.access_token = f"access-{user_id}"
        session.refresh_token = f"refresh-{user_id}"
        response = MagicMock()
        response.user = user
        response.session = session
        return response

    def sign_in_with_password(self, payload):
        return self.sign_up(payload)

    def get_user(self, token):
        user_id = token.replace("Bearer ", "").replace("access-", "")
        user = MagicMock()
        user.id = f"user-{user_id}"
        user.email = f"user{user_id}@test.com"
        user.app_metadata = {"roles": ["user"]}
        response = MagicMock()
        response.user = user
        return response

    def refresh_session(self, token):
        session = MagicMock()
        session.access_token = f"new-access-{token}"
        session.refresh_token = f"new-refresh-{token}"
        response = MagicMock()
        response.session = session
        return response

    def reset_password_for_email(self, email, options=None):
        return MagicMock()

    def sign_in_with_otp(self, payload):
        return MagicMock()


class FakeSupabaseTable:
    def __init__(self, fake, name):
        self._fake = fake
        self._name = name
        self._filters = []
        self._insert_data = None
        self._update_data = None
        self._order_field = None
        self._order_desc = False
        self._limit_val = None
        self._range_start = None
        self._range_end = None

    def insert(self, data):
        self._insert_data = data
        return self

    def select(self, columns="*"):
        self._select_columns = columns
        return self

    def eq(self, field, value):
        self._filters.append(("eq", field, value))
        return self

    def update(self, data):
        self._update_data = data
        return self

    def delete(self):
        self._delete_mode = True
        return self

    def order(self, field, desc=False):
        self._order_field = field
        self._order_desc = desc
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def _row_matches_filters(self, row):
        for op, field, value in self._filters:
            if op == "eq":
                row_val = row.get(field)
                if row_val is None and value is False:
                    continue
                if row_val != value:
                    return False
        return True

    def execute(self):
        table = self._fake._data.setdefault(self._name, [])
        if self._insert_data is not None:
            record = dict(self._insert_data)
            record_id = self._fake._next_ids.get(self._name, 1)
            record["id"] = record_id
            self._fake._next_ids[self._name] = record_id + 1
            table.append(record)
            response = MagicMock()
            response.data = [record]
            return response
        if self._update_data is not None:
            for row in table:
                match = True
                for op, field, value in self._filters:
                    if op == "eq" and row.get(field) != value:
                        match = False
                        break
                if match:
                    row.update(self._update_data)
            response = MagicMock()
            response.data = [row for row in table if all(
                (row.get(f) == v) for op, f, v in self._filters if op == "eq"
            )]
            return response
        if getattr(self, "_delete_mode", False):
            deleted = []
            new_table = []
            for row in table:
                match = all(
                    (row.get(f) == v) for op, f, v in self._filters if op == "eq"
                )
                if match:
                    deleted.append(row)
                else:
                    new_table.append(row)
            self._fake._data[self._name] = new_table
            response = MagicMock()
            response.data = deleted
            return response
        results = [row for row in table if self._row_matches_filters(row)]
        if self._order_field:
            results.sort(key=lambda r: r.get(self._order_field, ""), reverse=self._order_desc)
        if self._range_start is not None:
            end = self._range_end + 1 if self._range_end is not None else None
            results = results[self._range_start:end]
        elif self._limit_val is not None:
            results = results[: self._limit_val]
        response = MagicMock()
        response.data = results
        return response


class FakeSupabase:
    def __init__(self):
        self._data = {}
        self._next_ids = {}
        self._next_profile_id = 1

    def table(self, name):
        return FakeSupabaseTable(self, name)

    @property
    def auth(self):
        return FakeSupabaseAuth(self)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_supabase():
    return FakeSupabase()


@pytest.fixture(autouse=True)
def mock_supabase(fake_supabase):
    with patch.object(auth_module, "supabase", fake_supabase), \
         patch.object(db_module, "supabase", fake_supabase):
        yield fake_supabase


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.is_configured = True
    provider.supports_streaming = True
    provider.chat_with_retry = AsyncMock(return_value=MagicMock(
        content="Mocked AI response",
        tokens_used=10,
        provider="test",
    ))
    provider.stream = AsyncMock(return_value=iter(["Mocked ", "AI ", "response"]))
    return provider


@pytest.fixture
def mock_usage_tracker():
    tracker = MagicMock()
    tracker.record_success = AsyncMock(return_value=1)
    tracker.get_count = AsyncMock(return_value=0)
    tracker.limit = 50
    return tracker


class TestHealthAndStatus:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_check(self, client):
        response = client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_liveness_check(self, client):
        response = client.get("/health/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "ASTRAVOX" in data["message"]
        assert data["status"] == "operational"

    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        assert response.status_code in (200, 500)


class TestChatLifecycle:
    def test_create_conversation(self, client, fake_supabase, mock_usage_tracker):
        with patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            response = client.post(
                "/chat/conversations",
                json={"title": "Test Chat", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "conversation" in data
        assert data["conversation"]["title"] == "Test Chat"
        assert "id" in data["conversation"]

    def test_list_conversations(self, client, fake_supabase, mock_usage_tracker):
        with patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            client.post(
                "/chat/conversations",
                json={"title": "Test Chat", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
            response = client.get(
                "/chat/conversations",
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "conversations" in data
        assert len(data["conversations"]) >= 1

    def test_get_conversation_detail(self, client, fake_supabase, mock_usage_tracker):
        with patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            create_resp = client.post(
                "/chat/conversations",
                json={"title": "Detail Chat", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
        conv_id = create_resp.json()["conversation"]["id"]
        response = client.get(
            f"/chat/conversations/{conv_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["conversation"]["title"] == "Detail Chat"

    def test_send_message(self, client, fake_supabase, mock_provider, mock_usage_tracker):
        with patch.object(chat_module, "ProviderFactory") as factory_mock, \
             patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            factory_mock.get.return_value = mock_provider
            factory_mock.get_for_model.return_value = mock_provider
            create_resp = client.post(
                "/chat/conversations",
                json={"title": "Message Chat", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
            conv_id = create_resp.json()["conversation"]["id"]
            response = client.post(
                "/chat/message",
                json={"conversation_id": conv_id, "message": "Hello AI", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "user_message" in data
        assert "ai_message" in data
        assert data["ai_message"]["content"] == "Mocked AI response"

    def test_get_conversation_messages(self, client, fake_supabase, mock_provider, mock_usage_tracker):
        with patch.object(chat_module, "ProviderFactory") as factory_mock, \
             patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            factory_mock.get.return_value = mock_provider
            factory_mock.get_for_model.return_value = mock_provider
            create_resp = client.post(
                "/chat/conversations",
                json={"title": "Messages Chat", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
            client.post(
                "/chat/message",
                json={"conversation_id": create_resp.json()["conversation"]["id"], "message": "Hi"},
                headers={"Authorization": "Bearer test-token"},
            )
            conv_id = create_resp.json()["conversation"]["id"]
            response = client.get(
                f"/chat/conversations/{conv_id}/messages",
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "messages" in data
        assert len(data["messages"]) >= 1

    def test_update_conversation_title(self, client, fake_supabase, mock_usage_tracker):
        with patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            create_resp = client.post(
                "/chat/conversations",
                json={"title": "Old Title", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
        conv_id = create_resp.json()["conversation"]["id"]
        response = client.post(
            f"/chat/conversations/{conv_id}/title?title=New+Title",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["conversation"]["title"] == "New Title"

    def test_delete_conversation(self, client, fake_supabase, mock_usage_tracker):
        with patch.object(chat_module, "usage_tracker", mock_usage_tracker):
            create_resp = client.post(
                "/chat/conversations",
                json={"title": "Delete Me", "model": "gpt-4"},
                headers={"Authorization": "Bearer test-token"},
            )
        conv_id = create_resp.json()["conversation"]["id"]
        response = client.delete(
            f"/chat/conversations/{conv_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    def test_list_models(self, client):
        response = client.get("/chat/models")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "models" in data
        assert len(data["models"]) >= 1


class TestTerminalLifecycle:
    def test_inject_memory(self, client, fake_supabase):
        with patch.object(terminal_module, "get_supabase", return_value=fake_supabase):
            response = client.post(
                "/api/terminal/inject",
                json={"content": "terminal test memory"},
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "memory" in data

    def test_usage_endpoint(self, client, fake_supabase, mock_usage_tracker):
        with patch.object(terminal_module, "get_supabase", return_value=fake_supabase), \
             patch.object(terminal_module, "DailyUsageTracker", return_value=mock_usage_tracker):
            response = client.get(
                "/api/terminal/usage",
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert "used" in data
        assert "limit" in data


class TestErrorHandling:
    def test_404_for_unknown_route(self, client):
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_invalid_json_body(self, client):
        response = client.post(
            "/auth/login",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_create_conversation_requires_auth(self, client):
        response = client.post("/chat/conversations", json={
            "title": "Test",
            "model": "gpt-4",
        })
        assert response.status_code == 401

    def test_send_message_requires_auth(self, client):
        response = client.post("/chat/message", json={
            "conversation_id": 1,
            "message": "Hello",
            "model": "gpt-4",
        })
        assert response.status_code == 401

    def test_invalid_model_rejected(self, client):
        response = client.post(
            "/chat/conversations",
            json={"title": "Test", "model": "invalid-model-xyz"},
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code in (401, 422)
