import sqlite3
from database.transaction import transaction


def _make_conn(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "tx.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            balance REAL NOT NULL
        );
    """)
    conn.commit()
    return conn


def test_transaction_commits_on_success(tmp_path):
    conn = _make_conn(tmp_path)
    with transaction(conn):
        conn.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", ("alice", 100.0))
    row = conn.execute("SELECT balance FROM accounts WHERE name=?", ("alice",)).fetchone()
    assert row["balance"] == 100.0
    conn.close()


def test_transaction_rolls_back_on_exception(tmp_path):
    conn = _make_conn(tmp_path)
    try:
        with transaction(conn):
            conn.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", ("alice", 100.0))
            raise RuntimeError("fail")
    except RuntimeError:
        pass
    row = conn.execute("SELECT balance FROM accounts WHERE name=?", ("alice",)).fetchone()
    assert row is None
    conn.close()


def test_transaction_creates_and_closes_connection_when_none(tmp_path):
    db_path = str(tmp_path / "auto.db")
    with transaction() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO items (id) VALUES (1)")
    # Connection should be closed after exiting context
    new_conn = sqlite3.connect(db_path)
    count = new_conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
    new_conn.close()
    assert count == 1
