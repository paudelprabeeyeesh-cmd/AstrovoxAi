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


def test_execute_returns_cursor(tmp_path):
    repo = _make_repo(tmp_path)
    cur = repo.execute("INSERT INTO items (name, value) VALUES (?, ?)", ("x", 1.0))
    assert cur.lastrowid is not None


def test_fetchone_returns_dict_or_none(tmp_path):
    repo = _make_repo(tmp_path)
    assert repo.fetchone("SELECT * FROM items WHERE name=?", ("missing",)) is None
    repo.insert({"name": "widget", "value": 9.5})
    row = repo.fetchone("SELECT * FROM items WHERE name=?", ("widget",))
    assert row["name"] == "widget"


def test_fetchall_returns_list_of_dicts(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "a", "value": 1.0})
    repo.insert({"name": "b", "value": 2.0})
    rows = repo.fetchall("SELECT * FROM items")
    assert len(rows) == 2
    assert all(isinstance(r, dict) for r in rows)


def test_find_by_id_with_custom_pk_name(tmp_path):
    repo = _make_repo(tmp_path)
    row_id = repo.insert({"name": "widget", "value": 9.5})
    row = repo.find_by_id(row_id, pk_name="id")
    assert row["name"] == "widget"


def test_update_returns_zero_when_no_match(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "widget", "value": 9.5})
    count = repo.update({"name": "gadget"}, "id=?", (999,))
    assert count == 0


def test_delete_returns_zero_when_no_match(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "widget", "value": 9.5})
    count = repo.delete("id=?", (999,))
    assert count == 0


def test_find_all_with_params(tmp_path):
    repo = _make_repo(tmp_path)
    repo.insert({"name": "a", "value": 1.0})
    repo.insert({"name": "b", "value": 2.0})
    rows = repo.find_all("SELECT * FROM items WHERE value > ?", (1.5,))
    assert len(rows) == 1
    assert rows[0]["name"] == "b"


def test_insert_single_key(tmp_path):
    repo = _make_repo(tmp_path)
    row_id = repo.insert({"name": "only_name"})
    assert row_id == 1
    assert repo.find_by_id(row_id)["name"] == "only_name"
