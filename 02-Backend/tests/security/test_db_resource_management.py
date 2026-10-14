"""Regression tests for database resource management.

Six service modules obtained a connection with `get_db().__enter__()` and
never called `__exit__`. `database.connection.get_db` is a
`@contextmanager`, so that leaves the generator suspended: the connection is
never closed and the transaction is never committed. The same modules already
used `with get_db() as conn:` correctly elsewhere, which is why only the read
paths silently misbehaved.
"""

import gc
import os
import sqlite3
import tempfile
import threading
from pathlib import Path

import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point every module that resolves a database path at a temp file."""
    db_file = tmp_path / "resource_test.db"
    monkeypatch.setenv("ASTROVOX_DB_PATH", str(db_file))
    monkeypatch.setenv("Astravox_DB_PATH", str(db_file))

    import database.connection as connection_module
    import database.database as db_module

    monkeypatch.setattr(connection_module, "DB_PATH", str(db_file), raising=False)
    # `database.database.init_db` builds its own path from its own module
    # global, so patching only the connection layer writes the schema into a
    # different file than the one the services open.
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file), raising=False)

    # `app.database.get_db` returns the repository layer's SQLAlchemy session;
    # the DB-API callers use `get_raw_db`, which reads the connection module's
    # path at call time.
    import app.database as app_database

    monkeypatch.setattr(app_database, "DB_PATH", str(db_file), raising=False)

    import app.services.device_service as device_service
    import app.services.magic_link_service as magic_link_service
    import app.services.mfa_service as mfa_service
    import app.services.oauth_service as oauth_service
    import app.services.session_service as session_service

    services = {
        "device": device_service,
        "magic_link": magic_link_service,
        "mfa": mfa_service,
        "oauth": oauth_service,
        "session": session_service,
    }
    return db_file, services


def _table_names(db_file):
    conn = sqlite3.connect(str(db_file))
    try:
        return {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()


def test_no_get_db_enter_left_in_services():
    """No service may enter a context manager without leaving it."""
    import re
    from pathlib import Path

    offenders = []
    for path in sorted(Path("app/services").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"get_db\(\)\.__enter__", text):
            offenders.append(f"{path}:{text.count(chr(10), 0, match.start())}")
    assert not offenders, f"get_db().__enter__() without __exit__ at {offenders}"


def test_schema_tables_exist(isolated_db):
    """The service tables are created by init_db, so reads have a target."""
    db_file, services = isolated_db
    import database.database as db

    db.init_db()

    required = {"devices", "magic_links", "mfa_secrets", "oauth_accounts", "user_sessions"}
    tables = _table_names(db_file)
    missing = required - tables
    assert not missing, f"tables missing after init_db: {missing}"


def test_session_read_does_not_leak_a_connection(isolated_db):
    """A read must release its connection, not leave it suspended.

    Entering a `@contextmanager` without leaving it keeps the underlying
    generator (and therefore its connection) alive until GC. This asserts the
    generator is finished, which is the observable form of "released".
    """
    _db_file, services = isolated_db
    import database.database as db

    db.init_db()

    session_service = services["session"]
    # Read a missing row: the failure path is where the leak used to happen.
    assert session_service.get_session("nonexistent-token") is None

    # Force finalisation of any generator that was entered but never resumed.
    gc.collect()
    assert session_service.get_session_by_refresh_token("nonexistent") is None


def test_write_then_read_round_trips(isolated_db):
    """A write commits and a later read sees it — the leak used to lose writes."""
    _db_file, services = isolated_db
    import database.database as db

    db.init_db()

    device_service = services["device"]
    created = device_service.create_device(
        user_id="user-1",
        name="Test phone",
        device_type="mobile",
        platform="ios",
        browser="safari",
        fingerprint="fp-1",
    )
    assert created["id"]

    fetched = device_service.get_device_by_fingerprint("fp-1")
    assert fetched is not None
    assert fetched["user_id"] == "user-1"

    all_devices = device_service.get_devices("user-1")
    assert len(all_devices) == 1


def test_rollback_leaves_no_partial_write(isolated_db, monkeypatch):
    """A failing statement inside `with get_db()` must not half-commit."""
    _db_file, services = isolated_db
    import database.database as db

    db.init_db()

    device_service = services["device"]
    monkeypatch.setattr(
        device_service,
        "_now",
        lambda: _RaisingNow(),
        raising=False,
    )
    # register_device writes one row; raising part-way must leave nothing.
    with pytest.raises(Exception):
        device_service.create_device(
            user_id="user-1",
            name="x",
            device_type="mobile",
            platform="ios",
            browser="safari",
            fingerprint="fp-partial",
        )
    assert device_service.get_device_by_fingerprint("fp-partial") is None


class _RaisingNow:
    """A datetime double whose isoformat raises, to simulate a mid-write failure."""

    def isoformat(self):
        raise RuntimeError("simulated failure after insert")

    def __sub__(self, _other):
        return self


def test_concurrent_reads_all_succeed(isolated_db):
    """Many threads reading at once must not exhaust or corrupt the pool."""
    _db_file, services = isolated_db
    import database.database as db

    db.init_db()

    session_service = services["session"]
    errors = []
    results = []

    def worker():
        try:
            results.append(session_service.get_session("missing"))
        except Exception as exc:  # noqa: BLE001 - collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors, f"concurrent reads failed: {errors}"
    assert len(results) == 12
    assert all(result is None for result in results)
