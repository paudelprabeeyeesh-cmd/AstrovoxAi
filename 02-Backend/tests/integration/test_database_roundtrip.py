"""Database write/read round-trip integration tests."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app import auth as auth_module
from app import database as db_module
from app import chat as chat_module

from database.database import (
    init_db,
    create_user,
    get_user_by_username_or_email,
    verify_user_credentials,
    update_user_last_login,
    save_chat_message,
    get_conversation_history,
    increment_usage,
    get_db,
)


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
                if self._row_matches_filters(row):
                    row.update(self._update_data)
            response = MagicMock()
            response.data = [row for row in table if self._row_matches_filters(row)]
            return response
        if getattr(self, "_delete_mode", False):
            deleted = []
            new_table = []
            for row in table:
                if self._row_matches_filters(row):
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
def tmp_db_path(tmp_path):
    db_file = tmp_path / "test_chat.db"
    with patch("database.database.DB_PATH", str(db_file)):
        init_db()
        yield str(db_file)


class TestLocalDatabaseRoundtrip:
    def test_user_roundtrip(self, tmp_db_path):
        user_id = create_user("testuser", "test@example.com", "password123")
        assert user_id is not None
        user = get_user_by_username_or_email("testuser")
        assert user is not None
        assert user["email"] == "test@example.com"
        verified = verify_user_credentials("testuser", "password123")
        assert verified is not None
        assert verified["id"] == user_id
        update_user_last_login(user_id)
        user_after = get_user_by_username_or_email("testuser")
        assert user_after["last_login"] is not None

    def test_chat_message_roundtrip(self, tmp_db_path):
        user_id = create_user("chatuser", "chat@example.com", "pass123")
        save_chat_message("conv-1", str(user_id), "user", "Hello")
        save_chat_message("conv-1", str(user_id), "assistant", "Hi there")
        history = get_conversation_history("conv-1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["message"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["message"] == "Hi there"

    def test_usage_tracking_roundtrip(self, tmp_db_path):
        user_id = create_user("usageuser", "usage@example.com", "pass123")
        increment_usage(str(user_id))
        conn = get_db()
        cur = conn.execute(
            "SELECT * FROM usage WHERE user_id = ? AND kind = ?",
            (str(user_id), "questions"),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row["used"] == 1


class TestAppDatabaseRoundtrip:
    def test_conversation_roundtrip(self, client, fake_supabase):
        response = client.post(
            "/chat/conversations",
            json={"title": "Roundtrip Chat", "model": "gpt-4"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        conv = response.json()["conversation"]
        conv_id = conv["id"]
        assert conv["title"] == "Roundtrip Chat"
        response = client.get(
            f"/chat/conversations/{conv_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        assert response.json()["conversation"]["title"] == "Roundtrip Chat"

    def test_message_roundtrip(self, client, fake_supabase):
        create_resp = client.post(
            "/chat/conversations",
            json={"title": "Msg Roundtrip", "model": "gpt-4"},
            headers={"Authorization": "Bearer test-token"},
        )
        conv_id = create_resp.json()["conversation"]["id"]
        msg_payload = {
            "conversation_id": conv_id,
            "message": "Test message content",
            "model": "gpt-4",
        }
        with patch.object(chat_module, "ProviderFactory") as factory_mock:
            mock_provider = MagicMock()
            mock_provider.is_configured = True
            mock_provider.supports_streaming = True
            mock_provider.chat_with_retry = AsyncMock(return_value=MagicMock(
                content="Mocked AI response",
                tokens_used=10,
                provider="test",
            ))
            factory_mock.get.return_value = mock_provider
            factory_mock.get_for_model.return_value = mock_provider
            response = client.post(
                "/chat/message",
                json=msg_payload,
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["user_message"]["content"] == "Test message content"
        assert data["ai_message"]["content"] == "Mocked AI response"
        response = client.get(
            f"/chat/conversations/{conv_id}/messages",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        messages = response.json()["messages"]
        assert len(messages) >= 1
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) >= 1
        assert user_msgs[0]["content"] == "Test message content"

    def test_conversation_list_after_create(self, client, fake_supabase):
        client.post(
            "/chat/conversations",
            json={"title": "First", "model": "gpt-4"},
            headers={"Authorization": "Bearer test-token"},
        )
        client.post(
            "/chat/conversations",
            json={"title": "Second", "model": "gpt-4"},
            headers={"Authorization": "Bearer test-token"},
        )
        response = client.get(
            "/chat/conversations",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        titles = [c["title"] for c in data["conversations"]]
        assert "First" in titles
        assert "Second" in titles
