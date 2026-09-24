import sqlite3
from database.migration_runner import MigrationRunner, run_migrations


def _make_runner(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "mig.db"))
    conn.row_factory = sqlite3.Row
    return MigrationRunner(conn)


def test_applied_versions_empty_initially(tmp_path):
    runner = _make_runner(tmp_path)
    assert runner.applied_versions() == []


def test_run_applies_pending_migrations(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "mig.db"))
    conn.row_factory = sqlite3.Row
    runner = MigrationRunner(conn)
    migrations = [
        (1, "create_table", "CREATE TABLE foo (id INTEGER PRIMARY KEY);"),
        (2, "add_column", "ALTER TABLE foo ADD COLUMN bar TEXT;"),
    ]
    runner.run(migrations)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='foo'").fetchall()
    assert len(rows) == 1
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(foo)").fetchall()]
    assert "bar" in cols


def test_run_skips_already_applied(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "mig.db"))
    conn.row_factory = sqlite3.Row
    runner = MigrationRunner(conn)
    migrations = [(1, "create_table", "CREATE TABLE foo (id INTEGER PRIMARY KEY);")]
    runner.run(migrations)
    # Running again should not raise
    runner.run(migrations)


def test_pending_returns_unapplied(tmp_path):
    runner = _make_runner(tmp_path)
    migrations = [(1, "a", "CREATE TABLE t1 (id INTEGER PRIMARY KEY);"),
                  (2, "b", "CREATE TABLE t2 (id INTEGER PRIMARY KEY);")]
    pending = runner.pending(migrations)
    assert len(pending) == 2
    runner.run(migrations)
    pending = runner.pending(migrations)
    assert pending == []


def test_run_migrations_wrapper(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "mig.db"))
    conn.row_factory = sqlite3.Row
    migrations = [(1, "create_table", "CREATE TABLE foo (id INTEGER PRIMARY KEY);")]
    run_migrations(conn, migrations)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='foo'").fetchall()
    assert len(rows) == 1
