import sqlite3

import pytest

from database.connection import init_db, get_connection
from database.migration_runner import MigrationRunner


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "mig.db")
    init_db(path)
    return get_connection(path)


def test_run_new_migrations(conn):
    runner = MigrationRunner(conn)
    migrations = [
        (1, "add_note", "ALTER TABLE users ADD COLUMN note TEXT;"),
        (2, "add_flag", "ALTER TABLE users ADD COLUMN flag INTEGER DEFAULT 0;"),
    ]
    runner.run(migrations)
    versions = runner.applied_versions()
    assert versions == [1, 2]


def test_skip_already_applied(conn):
    runner = MigrationRunner(conn)
    sql = "ALTER TABLE users ADD COLUMN skipped TEXT;"
    runner.run([(1, "first", sql)])
    runner.run([(1, "first", sql)])
    versions = runner.applied_versions()
    assert versions == [1]


def test_pending_returns_unapplied(conn):
    runner = MigrationRunner(conn)
    migrations = [
        (1, "a", "ALTER TABLE users ADD COLUMN a TEXT;"),
        (2, "b", "ALTER TABLE users ADD COLUMN b TEXT;"),
    ]
    assert runner.pending(migrations) == migrations
    runner.run(migrations)
    assert runner.pending(migrations) == []
