import os
import sqlite3

import pytest

from database.connection import DB_PATH, get_connection, init_db


def test_get_connection_returns_sqlite_connection(tmp_path):
    target = str(tmp_path / "test.db")
    conn = get_connection(target)
    try:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory is not None
    finally:
        conn.close()
        if os.path.exists(target):
            os.remove(target)


def test_init_db_creates_tables(tmp_path):
    target = str(tmp_path / "init.db")
    init_db(target)
    conn = sqlite3.connect(target)
    try:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "users" in tables
        assert "chats" in tables
        assert "usage" in tables
        assert "schema_migrations" in tables
    finally:
        conn.close()
        if os.path.exists(target):
            os.remove(target)


def test_db_path_defaults_to_app_db():
    assert DB_PATH.endswith("app.db")
