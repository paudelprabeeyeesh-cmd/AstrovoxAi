from __future__ import annotations

import pytest

from memory_persistence.incognito_mode import IncognitoMode


@pytest.fixture
def manager():
    return IncognitoMode()


def test_start_session(manager):
    session = manager.start_session("s1")
    assert session is not None
    assert session._session_id == "s1"


def test_start_duplicate_session(manager):
    manager.start_session("s1")
    with pytest.raises(ValueError):
        manager.start_session("s1")


def test_get_session(manager):
    manager.start_session("s1")
    assert manager.get_session("s1") is not None
    assert manager.get_session("missing") is None


def test_end_session(manager):
    manager.start_session("s1")
    result = manager.end_session("s1")
    assert result["status"] == "ended"
    assert manager.get_session("s1") is None


def test_end_missing_session(manager):
    assert manager.end_session("missing") is None


def test_add_turn(manager):
    session = manager.start_session("s1")
    turn = session.add_turn("user", "hello")
    assert turn.content == "hello"
    assert turn.role == "user"


def test_add_turn_after_end(manager):
    session = manager.start_session("s1")
    session.end_session()
    with pytest.raises(RuntimeError):
        session.add_turn("user", "hello")


def test_get_turns(manager):
    session = manager.start_session("s1")
    session.add_turn("user", "hello")
    session.add_turn("assistant", "hi")
    turns = session.get_turns()
    assert len(turns) == 2


def test_get_turns_pagination(manager):
    session = manager.start_session("s1")
    for i in range(3):
        session.add_turn("user", f"msg{i}")
    turns = session.get_turns(limit=1, offset=1)
    assert len(turns) == 1
    assert turns[0].content == "msg1"


def test_get_session_info(manager):
    session = manager.start_session("s1")
    info = session.get_session_info()
    assert info["session_id"] == "s1"
    assert info["mode"] == "incognito"
    assert info["turn_count"] == 0


def test_end_session_clears_data(manager):
    session = manager.start_session("s1")
    session.add_turn("user", "secret")
    result = session.end_session()
    assert result["data_retained"] is False
    assert result["turns_processed"] == 1
    assert session.get_turns() == []


def test_global_incognito(manager):
    assert manager.is_global_incognito() is False
    manager.enable_global_incognito()
    assert manager.is_global_incognito() is True
    manager.disable_global_incognito()
    assert manager.is_global_incognito() is False


def test_ensure_no_leak_safe(manager):
    assert manager.ensure_no_leak("hello world") is True


def test_ensure_no_leak_email(manager):
    assert manager.ensure_no_leak("contact me at test@example.com") is False


def test_ensure_no_leak_phone(manager):
    assert manager.ensure_no_leak("call 555-123-4567") is False


def test_ensure_no_leak_api_key(manager):
    assert manager.ensure_no_leak("my api_key is secret123") is False
