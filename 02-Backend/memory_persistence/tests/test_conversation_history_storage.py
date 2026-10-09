from __future__ import annotations

import pytest

from memory_persistence.conversation_history_storage import (
    ConversationHistoryStorage,
)


@pytest.fixture
def storage():
    return ConversationHistoryStorage()


def test_create_conversation(storage):
    conv = storage.create_conversation(user_id="u1", title="Test")
    assert conv.user_id == "u1"
    assert conv.title == "Test"
    assert conv.conversation_id in storage._conversations


def test_add_message(storage):
    conv = storage.create_conversation(user_id="u1")
    msg = storage.add_message(conv.conversation_id, role="user", content="hello")
    assert msg.content == "hello"
    assert msg.role == "user"


def test_add_message_missing_conversation(storage):
    with pytest.raises(ValueError):
        storage.add_message("missing", role="user", content="hello")


def test_soft_delete_conversation(storage):
    conv = storage.create_conversation(user_id="u1")
    assert storage.soft_delete_conversation(conv.conversation_id) is True
    assert storage.get_conversation(conv.conversation_id) is None


def test_soft_delete_message(storage):
    conv = storage.create_conversation(user_id="u1")
    msg = storage.add_message(conv.conversation_id, role="user", content="hi")
    assert storage.soft_delete_message(msg.message_id) is True
    msgs = storage.get_messages(conv.conversation_id)
    assert msgs == []


def test_get_user_conversations(storage):
    c1 = storage.create_conversation(user_id="u1", title="A")
    storage.create_conversation(user_id="u2", title="B")
    c3 = storage.create_conversation(user_id="u1", title="C")
    convs = storage.get_user_conversations("u1")
    assert len(convs) == 2
    assert set(c.conversation_id for c in convs) == {c1.conversation_id, c3.conversation_id}


def test_search_messages(storage):
    conv = storage.create_conversation(user_id="u1")
    storage.add_message(conv.conversation_id, role="user", content="hello world")
    storage.add_message(conv.conversation_id, role="assistant", content="goodbye")
    results = storage.search_messages("u1", "hello")
    assert len(results) == 1
    assert results[0][1].content == "hello world"


def test_get_messages_pagination(storage):
    conv = storage.create_conversation(user_id="u1")
    for i in range(5):
        storage.add_message(conv.conversation_id, role="user", content=f"msg{i}")
    msgs = storage.get_messages(conv.conversation_id, limit=2, offset=1)
    assert len(msgs) == 2
    assert msgs[0].content == "msg1"


def test_get_stats(storage):
    storage.create_conversation(user_id="u1")
    stats = storage.get_stats()
    assert stats["total_conversations"] == 1
    assert stats["total_users"] == 1
