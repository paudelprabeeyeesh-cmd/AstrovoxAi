import sqlite3
from database.schema_manager import SchemaManager


def _make_manager(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "schema.db"))
    conn.row_factory = sqlite3.Row
    return SchemaManager(conn)


def test_applied_versions_empty_initially(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.applied_versions() == []


def test_pending_returns_unapplied(tmp_path):
    mgr = _make_manager(tmp_path)
    migrations = [
        (1, "create_table", "CREATE TABLE foo (id INTEGER PRIMARY KEY);"),
        (2, "add_column", "ALTER TABLE foo ADD COLUMN bar TEXT;"),
    ]
    pending = mgr.pending(migrations)
    assert len(pending) == 2


def test_run_applies_migrations(tmp_path):
    mgr = _make_manager(tmp_path)
    migrations = [
        (1, "create_table", "CREATE TABLE foo (id INTEGER PRIMARY KEY);"),
    ]
    mgr.run(migrations)
    assert mgr.applied_versions() == [1]


def test_run_skips_already_applied(tmp_path):
    mgr = _make_manager(tmp_path)
    migrations = [
        (1, "create_table", "CREATE TABLE foo (id INTEGER PRIMARY KEY);"),
    ]
    mgr.run(migrations)
    # Should not raise on second run
    mgr.run(migrations)
    assert mgr.applied_versions() == [1]


def test_create_table(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_table("widgets", {"id": "INTEGER PRIMARY KEY", "name": "TEXT NOT NULL"})
    conn = sqlite3.connect(str(tmp_path / "schema.db"))
    conn.row_factory = sqlite3.Row
    tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "widgets" in tables


def test_add_column_when_missing(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_table("widgets", {"id": "INTEGER PRIMARY KEY", "name": "TEXT NOT NULL"})
    mgr.add_column("widgets", "price", "REAL")
    conn = sqlite3.connect(str(tmp_path / "schema.db"))
    conn.row_factory = sqlite3.Row
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(widgets)").fetchall()]
    conn.close()
    assert "price" in cols


def test_add_column_when_exists(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_table("widgets", {"id": "INTEGER PRIMARY KEY", "name": "TEXT NOT NULL"})
    # Should not raise when adding an existing column
    mgr.add_column("widgets", "name", "TEXT")
    conn = sqlite3.connect(str(tmp_path / "schema.db"))
    conn.row_factory = sqlite3.Row
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(widgets)").fetchall()]
    conn.close()
    assert cols.count("name") == 1
