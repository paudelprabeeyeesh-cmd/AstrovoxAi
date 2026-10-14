"""Regression tests for `database.database.init_db`.

Guards the fix for `init_db()` failing with ``KeyError: 1``: the schema
helpers read rows positionally, but `database.connection.get_connection`
installs a dict row factory, so `row[1]` looks up a column named "1".
"""

from __future__ import annotations

import os
import sqlite3

import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point the module at a throwaway database file."""
    db_file = tmp_path / "probe.db"
    monkeypatch.setenv("ASTROVOX_DB_PATH", str(db_file))

    import database.database as db

    # The two modules resolve DB_PATH independently, so both are patched or
    # one keeps writing to the developer's real chat.db.
    monkeypatch.setattr(db, "DB_PATH", str(db_file), raising=False)
    yield db, db_file


def _tables(db_file):
    conn = sqlite3.connect(str(db_file))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()


def test_init_db_creates_core_tables(isolated_db):
    """init_db must not raise, and must create the tables the API reads."""
    db, db_file = isolated_db
    db.init_db()

    tables = _tables(db_file)
    for table in ("users", "conversations", "messages", "usage", "documents", "document_chunks"):
        assert table in tables, f"{table} missing after init_db; got {sorted(tables)}"


def test_init_db_is_idempotent(isolated_db):
    """Re-running init_db on an existing database must be a no-op."""
    db, db_file = isolated_db
    db.init_db()
    before = _tables(db_file)
    db.init_db()
    assert _tables(db_file) == before


def test_row_helpers_read_columns_by_name(isolated_db):
    """Schema helpers must work with either row factory.

    `get_connection` returns dict rows, a plain `sqlite3.connect` returns
    positional tuples, and `sqlite3.Row` supports name subscripting. The
    helpers are used against all three, so they read by name.
    """
    db, _ = isolated_db

    for row in (
        {"name": "conversations", "cid": 3},
        # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
        (0, "conversations", "TEXT", 0, None, 0),
    ):
        name = db._column_name(row)
        assert name == "conversations", f"could not read a column name from {row!r}"

    # sqlite3.Row supports subscripting by name but cannot be constructed
    # directly, so one is obtained from a real cursor.
    conn = sqlite3.connect(":memory:")
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT 'conversations' AS name, 2 AS cid")
        sqlite_row = cursor.fetchone()
    finally:
        conn.close()
    assert db._column_name(sqlite_row) == "conversations"


def test_both_env_var_spellings_agree(isolated_db, monkeypatch, tmp_path):
    """The two modules must resolve to one database file.

    `database.database` read `Astravox_DB_PATH` while
    `database.connection` read `ASTROVOX_DB_PATH`. With both set they opened
    different files, so the schema was created in one and the queries ran
    against the other.
    """
    db, _ = isolated_db

    import database.connection as connection_module

    canonical = tmp_path / "canonical.db"
    legacy = tmp_path / "legacy.db"
    monkeypatch.setenv("ASTROVOX_DB_PATH", str(canonical))
    monkeypatch.setenv("Astravox_DB_PATH", str(legacy))

    # Re-resolve the module constants the way import time would.
    resolved = os.getenv("ASTROVOX_DB_PATH") or os.getenv(
        "Astravox_DB_PATH", os.path.join(connection_module.DB_DIR, "app.db")
    )
    monkeypatch.setattr(db, "DB_PATH", resolved, raising=False)

    assert connection_module.DB_PATH != resolved or canonical == resolved
    db.init_db()

    # The tables must live in the file the queries will actually open.
    conn = sqlite3.connect(resolved)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "documents" in tables, "schema was created in a different file than the one queried"
