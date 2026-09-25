"""Comprehensive database operation tests."""

import os
import uuid
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.database import (
    get_user_profile,
    create_user_profile,
    update_user_profile,
    create_conversation,
    get_conversations,
    get_conversation,
    update_conversation,
    delete_conversation,
    create_message,
    get_messages,
    get_recent_messages,
    save_memory,
    get_user_memory,
    get_user_settings,
    update_user_settings,
    ALLOWED_PROFILE_FIELDS,
    ALLOWED_CONVERSATION_FIELDS,
    ALLOWED_SETTINGS_FIELDS,
)


@pytest.fixture(autouse=True)
def mock_supabase():
    with patch("app.database.supabase") as mock_sb:
        yield mock_sb


class TestUserProfile:
    def test_get_user_profile_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "user-1", "username": "testuser", "full_name": "Test"}
        ]
        profile = pytest.run(lambda: get_user_profile("user-1"))
        assert profile["id"] == "user-1"

    def test_get_user_profile_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        profile = pytest.run(lambda: get_user_profile("nonexistent"))
        assert profile is None

    def test_get_user_profile_exception(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")
        profile = pytest.run(lambda: get_user_profile("user-1"))
        assert profile is None

    def test_create_user_profile(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "user-1", "username": "newuser", "full_name": "New User"}
        ]
        profile = pytest.run(lambda: create_user_profile("user-1", "newuser", full_name="New User"))
        assert profile["username"] == "newuser"

    def test_create_user_profile_failure(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Insert failed")
        profile = pytest.run(lambda: create_user_profile("user-1", "newuser"))
        assert profile is None

    def test_update_user_profile_allowed_fields(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "user-1", "full_name": "Updated Name"}
        ]
        profile = pytest.run(lambda: update_user_profile("user-1", full_name="Updated Name"))
        assert profile["full_name"] == "Updated Name"

    def test_update_user_profile_disallowed_fields_ignored(self, mock_supabase):
        profile = pytest.run(lambda: update_user_profile("user-1", is_admin=True))
        assert profile is None
        mock_supabase.table.assert_not_called()

    def test_update_user_profile_empty_kwargs(self, mock_supabase):
        profile = pytest.run(lambda: update_user_profile("user-1"))
        assert profile is None

    def test_update_user_profile_exception(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("Update failed")
        profile = pytest.run(lambda: update_user_profile("user-1", full_name="Test"))
        assert profile is None


class TestConversations:
    def test_create_conversation(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1, "user_id": "user-1", "title": "New Conversation", "model": "gpt-4"}
        ]
        conv = pytest.run(lambda: create_conversation("user-1", title="New Conversation", model="gpt-4"))
        assert conv["id"] == 1
        assert conv["model"] == "gpt-4"

    def test_create_conversation_default_title(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1, "user_id": "user-1", "title": "New Conversation"}
        ]
        conv = pytest.run(lambda: create_conversation("user-1"))
        assert conv["title"] == "New Conversation"

    def test_create_conversation_failure(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
        conv = pytest.run(lambda: create_conversation("user-1"))
        assert conv is None

    def test_get_conversations(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {"id": 1, "title": "Chat 1"},
            {"id": 2, "title": "Chat 2"},
        ]
        convs = pytest.run(lambda: get_conversations("user-1"))
        assert len(convs) == 2

    def test_get_conversations_empty(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
        convs = pytest.run(lambda: get_conversations("user-1"))
        assert convs == []

    def test_get_conversation_by_id(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "title": "Chat 1"}
        ]
        conv = pytest.run(lambda: get_conversation(1, user_id="user-1"))
        assert conv["id"] == 1

    def test_get_conversation_without_user_filter(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "title": "Chat 1"}
        ]
        conv = pytest.run(lambda: get_conversation(1))
        assert conv["id"] == 1

    def test_get_conversation_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        conv = pytest.run(lambda: get_conversation(999, user_id="user-1"))
        assert conv is None

    def test_update_conversation_allowed_fields(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "title": "Updated Title"}
        ]
        conv = pytest.run(lambda: update_conversation(1, title="Updated Title"))
        assert conv["title"] == "Updated Title"

    def test_update_conversation_disallowed_fields(self, mock_supabase):
        conv = pytest.run(lambda: update_conversation(1, user_id="other-user"))
        assert conv is None
        mock_supabase.table.assert_not_called()

    def test_update_conversation_failure(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("Update failed")
        conv = pytest.run(lambda: update_conversation(1, title="New Title"))
        assert conv is None

    def test_delete_conversation(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": 1}]
        result = pytest.run(lambda: delete_conversation(1))
        assert result is True

    def test_delete_conversation_failure(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("Delete failed")
        result = pytest.run(lambda: delete_conversation(1))
        assert result is False


class TestMessages:
    def test_create_message(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1, "conversation_id": 1, "role": "user", "content": "Hello"}
        ]
        msg = pytest.run(lambda: create_message(1, "user-1", "user", "Hello", model_used="gpt-4", tokens_used=10))
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"

    def test_create_message_failure(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Insert failed")
        msg = pytest.run(lambda: create_message(1, "user-1", "user", "Hello"))
        assert msg is None

    def test_get_messages(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {"id": 1, "role": "user", "content": "Hi"},
            {"id": 2, "role": "assistant", "content": "Hello!"},
        ]
        msgs = pytest.run(lambda: get_messages(1))
        assert len(msgs) == 2

    def test_get_messages_empty(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
        msgs = pytest.run(lambda: get_messages(1))
        assert msgs == []

    def test_get_recent_messages(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1, "role": "user", "content": "Latest"}
        ]
        msgs = pytest.run(lambda: get_recent_messages(1, limit=1))
        assert len(msgs) == 1

    def test_get_recent_messages_failure(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        msgs = pytest.run(lambda: get_recent_messages(1))
        assert msgs == []


class TestMemoryDB:
    def test_save_memory(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": 1, "user_id": "user-1", "content": "fact", "importance": 2}
        ]
        mem = pytest.run(lambda: save_memory("user-1", "fact", importance=2))
        assert mem["content"] == "fact"

    def test_save_memory_failure(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
        mem = pytest.run(lambda: save_memory("user-1", "fact"))
        assert mem is None

    def test_get_user_memory(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": 1, "content": "fact 1", "importance": 3},
            {"id": 2, "content": "fact 2", "importance": 1},
        ]
        mems = pytest.run(lambda: get_user_memory("user-1"))
        assert len(mems) == 2

    def test_get_user_memory_empty(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mems = pytest.run(lambda: get_user_memory("user-1"))
        assert mems == []

    def test_get_user_memory_failure(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        mems = pytest.run(lambda: get_user_memory("user-1"))
        assert mems == []


class TestSettings:
    def test_get_user_settings_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "user-1", "theme": "dark"}
        ]
        settings = pytest.run(lambda: get_user_settings("user-1"))
        assert settings["theme"] == "dark"

    def test_get_user_settings_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        settings = pytest.run(lambda: get_user_settings("user-1"))
        assert settings is None

    def test_update_user_settings_allowed(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "user-1", "theme": "light"}
        ]
        settings = pytest.run(lambda: update_user_settings("user-1", theme="light"))
        assert settings["theme"] == "light"

    def test_update_user_settings_disallowed(self, mock_supabase):
        settings = pytest.run(lambda: update_user_settings("user-1", secret_key="hacked"))
        assert settings is None
        mock_supabase.table.assert_not_called()

    def test_update_user_settings_failure(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB error")
        settings = pytest.run(lambda: update_user_settings("user-1", theme="dark"))
        assert settings is None


class TestAllowedFields:
    def test_profile_fields_whitelist(self):
        assert "full_name" in ALLOWED_PROFILE_FIELDS
        assert "is_admin" not in ALLOWED_PROFILE_FIELDS

    def test_conversation_fields_whitelist(self):
        assert "title" in ALLOWED_CONVERSATION_FIELDS
        assert "user_id" not in ALLOWED_CONVERSATION_FIELDS

    def test_settings_fields_whitelist(self):
        assert "theme" in ALLOWED_SETTINGS_FIELDS
        assert "password" not in ALLOWED_SETTINGS_FIELDS
