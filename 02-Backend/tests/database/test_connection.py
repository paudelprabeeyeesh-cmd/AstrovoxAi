import sqlite3
from database.connection import get_connection, init_db


def test_get_connection_returns_sqlite3_connection(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    try:
        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory is not None
    finally:
        conn.close()


def test_init_db_creates_tables(tmp_path):
    db_path = str(tmp_path / "init.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "users" in tables
        assert "chats" in tables
        assert "usage" in tables
        assert "schema_migrations" in tables
    finally:
        conn.close()


def test_row_factory_returns_dict(tmp_path):
    db_path = str(tmp_path / "row.db")
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                     ("alice", "alice@example.com", "hash", "2024-01-01T00:00:00"))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE username=?", ("alice",)).fetchone()
        assert isinstance(row, dict)
        assert row["username"] == "alice"
    finally:
        conn.close()


def test_wal_mode_enabled(tmp_path):
    db_path = str(tmp_path / "wal.db")
    conn = get_connection(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
    finally:
        conn.close()


def test_foreign_keys_enabled(tmp_path):
    db_path = str(tmp_path / "fk.db")
    conn = get_connection(db_path)
    try:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
    finally:
        conn.close()
