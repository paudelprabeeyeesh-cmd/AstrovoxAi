import sqlite3
from database.repository import Repository


def _make_repo(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "repo.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value REAL
        );
    """)
    conn.commit()
    return Repository(conn, "items")


def test_find_by_id_returns_none_when_missing(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.find_by_id(1) is None


def test_insert_returns_lastrowid(tmp_path):
    repo = _make_repo(tmp_path)
    row_id = repo.insert({"name": "widget", "value": 9.5})
    assert row_id == 1


def test_find_by_id_after_insert(tmp_path):
    repo = _make_repo(tmp_path)
    row_id = repo.insert({"name": "widget", "value": 9.5})
    row = repo.find_by_id(row_id)
    assert row["name"] == "widget"
    assert row["value"] == 9.5


def test_find_all_returns_all_rows(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "a", "value": 1.0})
    repo.insert({"name": "b", "value": 2.0})
    rows = repo.find_all("SELECT * FROM items")
    assert len(rows) == 2


def test_update_returns_rowcount(tmp_path):
    repo = _make_repo(tmp_path)
    row_id = repo.insert({"name": "widget", "value": 9.5})
    count = repo.update({"name": "gadget", "value": 10.0}, "id=?", (row_id,))
    assert count == 1
    assert repo.find_by_id(row_id)["name"] == "gadget"


def test_delete_returns_rowcount(tmp_path):
    repo = _make_repo(tmp_path)
    row_id = repo.insert({"name": "widget", "value": 9.5})
    count = repo.delete("id=?", (row_id,))
    assert count == 1
    assert repo.find_by_id(row_id) is None


def test_count_returns_correct_number(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "a", "value": 1.0})
    repo.insert({"name": "b", "value": 2.0})
    assert repo.count() == 2
    assert repo.count("name=?", ("a",)) == 1


def test_find_one_returns_single_row(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "widget", "value": 9.5})
    row = repo.find_one("SELECT * FROM items WHERE name=?", ("widget",))
    assert row["name"] == "widget"
