import sqlite3

import pytest

from database.connection import get_connection, init_db
from database.transaction import transaction


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "txn.db")


def test_transaction_commits(db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        with transaction(conn) as c:
            c.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("txn1", "txn1@example.com", "hash", "2026-01-01T00:00:00"),
            )
    finally:
        conn.close()
    conn2 = get_connection(db_path)
    try:
        row = conn2.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        assert row["c"] == 1
    finally:
        conn2.close()


def test_transaction_rolls_back_on_error(db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    with pytest.raises(ValueError):
        with transaction(conn) as c:
            c.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("txn2", "txn2@example.com", "hash", "2026-01-01T00:00:00"),
            )
            raise ValueError("fail")
    conn2 = get_connection(db_path)
    try:
        row = conn2.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        assert row["c"] == 0
    finally:
        conn2.close()


def test_transaction_manages_connection_when_none(db_path):
    init_db(db_path)
    with transaction() as c:
        c.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("txn3", "txn3@example.com", "hash", "2026-01-01T00:00:00"),
        )
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        assert row["c"] == 1
    finally:
        conn.close()
