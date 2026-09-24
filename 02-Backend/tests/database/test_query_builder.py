from database.query_builder import QueryBuilder


def test_select_default():
    qb = QueryBuilder("users")
    sql, params = qb.build_select()
    assert sql == "SELECT * FROM users"
    assert params == []


def test_select_with_columns():
    qb = QueryBuilder("users")
    qb.select(["id", "name"])
    sql, params = qb.build_select()
    assert sql == "SELECT id, name FROM users"
    assert params == []


def test_where_clause():
    qb = QueryBuilder("users")
    qb.where("age > ?", 18).where("active = ?", True)
    sql, params = qb.build_select()
    assert "WHERE age > ? AND active = ?" in sql
    assert params == [18, True]


def test_order_by():
    qb = QueryBuilder("users")
    qb.order_by("name", "DESC")
    sql, _ = qb.build_select()
    assert "ORDER BY name DESC" in sql


def test_limit_and_offset():
    qb = QueryBuilder("users")
    qb.limit(10).offset(5)
    sql, _ = qb.build_select()
    assert "LIMIT 10" in sql
    assert "OFFSET 5" in sql


def test_build_insert():
    qb = QueryBuilder("users")
    sql, params = qb.build_insert({"name": "alice", "age": 30})
    assert sql == "INSERT INTO users (name, age) VALUES (?, ?)"
    assert params == ["alice", 30]


def test_build_update():
    qb = QueryBuilder("users")
    qb.where("id = ?", 1)
    sql, params = qb.build_update({"name": "alice", "age": 30})
    assert sql == "UPDATE users SET name=?, age=? WHERE id = ?"
    assert params == ["alice", 30, 1]


def test_build_delete():
    qb = QueryBuilder("users")
    qb.where("id = ?", 1)
    sql, params = qb.build_delete()
    assert sql == "DELETE FROM users WHERE id = ?"
    assert params == [1]
