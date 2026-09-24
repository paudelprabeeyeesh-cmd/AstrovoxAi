import os
import sqlite3
from datetime import datetime
from unittest.mock import patch

from database.database import (
    check_limit,
    create_user,
    get_active_users,
    get_conversation_history,
    get_db,
    get_site_metrics,
    get_total_conversations,
    get_total_messages,
    get_total_usage_records,
    get_total_users,
    get_user_by_username_or_email,
    get_user_usage,
    get_user_usage_summary,
    increment_usage,
    init_db,
    save_chat_message,
    update_user_last_login,
    verify_user_credentials,
)


def _make_db_path(tmp_path, name="test_database.db"):
    return str(tmp_path / name)


def test_init_db_creates_tables(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    tables = [
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    conn.close()
    assert "users" in tables
    assert "chats" in tables
    assert "usage" in tables


def test_get_db_returns_connection_with_row_factory(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        conn = get_db()
    try:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row
    finally:
        conn.close()


def test_create_user_returns_id(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        user_id = create_user("alice", "alice@example.com", "secret")
    assert isinstance(user_id, int)
    assert user_id > 0


def test_create_user_raises_on_missing_fields(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        for username, email, password in [
            ("", "a@b.com", "secret"),
            ("alice", "", "secret"),
            ("alice", "a@b.com", ""),
        ]:
            try:
                create_user(username, email, password)
            except ValueError:
                pass
            else:
                raise AssertionError("Expected ValueError")


def test_create_user_raises_on_duplicate(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        create_user("alice", "alice@example.com", "secret")
        try:
            create_user("alice", "alice2@example.com", "secret")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
        try:
            create_user("alice2", "alice@example.com", "secret")
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_get_user_by_username_or_email(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        create_user("alice", "alice@example.com", "secret")
        user = get_user_by_username_or_email("alice")
    assert user is not None
    assert user["username"] == "alice"
    with patch("database.database.DB_PATH", db_path):
        user = get_user_by_username_or_email("alice@example.com")
    assert user is not None
    assert user["username"] == "alice"
    assert get_user_by_username_or_email("") is None
    with patch("database.database.DB_PATH", db_path):
        assert get_user_by_username_or_email("bob") is None


def test_verify_user_credentials(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        create_user("alice", "alice@example.com", "secret")
        user = verify_user_credentials("alice", "secret")
    assert user is not None
    assert user["username"] == "alice"
    with patch("database.database.DB_PATH", db_path):
        assert verify_user_credentials("alice", "wrong") is None
        assert verify_user_credentials("bob", "secret") is None


def test_update_user_last_login(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        user_id = create_user("alice", "alice@example.com", "secret")
        update_user_last_login(user_id)
    conn = get_db()
    row = conn.execute("SELECT last_login FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row["last_login"] is not None


def test_save_chat_message_and_history(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        save_chat_message("conv1", "user1", "user", "hello")
        save_chat_message("conv1", "user1", "assistant", "hi there")
        history = get_conversation_history("conv1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["message"] == "hello"
    assert history[1]["role"] == "assistant"
    with patch("database.database.DB_PATH", db_path):
        assert get_conversation_history("nonexistent") == []


def test_check_limit(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        user_id = create_user("alice", "alice@example.com", "secret")
        allowed, used, limit = check_limit(str(user_id), "free", "questions")
    assert allowed is True
    assert used == 0
    assert limit == 100
    with patch("database.database.DB_PATH", db_path):
        allowed, used, limit = check_limit("nonexistent", "free", "questions")
    assert allowed is True
    assert used == 0


def test_increment_usage_and_summary(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        user_id = create_user("alice", "alice@example.com", "secret")
        increment_usage(str(user_id), "questions")
        increment_usage(str(user_id), "questions")
        summary = get_user_usage_summary(str(user_id))
    assert "questions" in summary["summary"]
    assert summary["summary"]["questions"] == 2
    with patch("database.database.DB_PATH", db_path):
        usage = get_user_usage(str(user_id))
    assert usage["total_messages"] == 0


def test_get_total_users(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        assert get_total_users() == 0
        create_user("alice", "alice@example.com", "secret")
        assert get_total_users() == 1


def test_get_active_users(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        user_id = create_user("alice", "alice@example.com", "secret")
        assert get_active_users() == 0
        update_user_last_login(user_id)
        assert get_active_users() == 1


def test_get_total_messages(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        assert get_total_messages() == 0
        save_chat_message("conv1", "user1", "user", "hello")
        assert get_total_messages() == 1


def test_get_total_conversations(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        assert get_total_conversations() == 0
        save_chat_message("conv1", "user1", "user", "hello")
        save_chat_message("conv1", "user1", "assistant", "hi")
        save_chat_message("conv2", "user1", "user", "hey")
        assert get_total_conversations() == 2


def test_get_site_metrics(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        metrics = get_site_metrics()
    assert "total_users" in metrics
    assert "active_users" in metrics
    assert "total_messages" in metrics
    assert "total_conversations" in metrics
    assert "total_usage_records" in metrics
    for value in metrics.values():
        assert value == 0


def test_get_total_usage_records(tmp_path):
    db_path = _make_db_path(tmp_path)
    with patch("database.database.DB_PATH", db_path):
        init_db()
        assert get_total_usage_records() == 0
        user_id = create_user("alice", "alice@example.com", "secret")
        increment_usage(str(user_id), "questions")
        assert get_total_usage_records() == 1
