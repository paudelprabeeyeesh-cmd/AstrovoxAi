import sqlite3

import pytest

from database.connection import init_db, get_connection
from database.repository import Repository


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "repo.db")
    init_db(path)
    conn = get_connection(path)
    conn.execute("DELETE FROM users")
    conn.commit()
    yield conn
    conn.close()


def test_insert_returns_lastrowid(conn):
    repo = Repository(conn, "users")
    pk = repo.insert({
        "username": "alice",
        "email": "alice@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    assert pk == 1


def test_find_by_id(conn):
    repo = Repository(conn, "users")
    repo.insert({
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    row = repo.find_by_id(1)
    assert row["username"] == "bob"


def test_update_returns_rowcount(conn):
    repo = Repository(conn, "users")
    repo.insert({
        "username": "carol",
        "email": "carol@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    rows = repo.update({"username": "carol2"}, "id=?", (1,))
    assert rows == 1
    assert repo.find_by_id(1)["username"] == "carol2"


def test_delete_returns_rowcount(conn):
    repo = Repository(conn, "users")
    repo.insert({
        "username": "dave",
        "email": "dave@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    rows = repo.delete("id=?", (1,))
    assert rows == 1
    assert repo.find_by_id(1) is None


def test_count(conn):
    repo = Repository(conn, "users")
    repo.insert({
        "username": "eve",
        "email": "eve@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    assert repo.count() == 1
    assert repo.count("username=?", ("eve",)) == 1


def test_find_all(conn):
    repo = Repository(conn, "users")
    repo.insert({
        "username": "f1",
        "email": "f1@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    repo.insert({
        "username": "f2",
        "email": "f2@example.com",
        "password_hash": "hash",
        "created_at": "2026-01-01T00:00:00",
    })
    rows = repo.find_all("ORDER BY id ASC")
    assert len(rows) == 2
