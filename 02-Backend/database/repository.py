import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple


class Repository:
    def __init__(self, conn: sqlite3.Connection, table: str) -> None:
        self.conn = conn
        self.table = table

    def execute(self, sql: str, params: Tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def fetchone(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        row = self.execute(sql, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.execute(sql, params).fetchall()]

    def find_by_id(self, pk: Any, pk_name: str = "id") -> Optional[Dict[str, Any]]:
        return self.fetchone(
            f"SELECT * FROM {self.table} WHERE {pk_name}=? LIMIT 1", (pk,)
        )

    def find_one(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        return self.fetchone(sql, params)

    def find_all(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        return self.fetchall(sql, params)

    def insert(self, data: Dict[str, Any]) -> int:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {self.table} ({keys}) VALUES ({placeholders})"
        cur = self.execute(sql, tuple(data.values()))
        return cur.lastrowid

    def update(self, data: Dict[str, Any], where: str, params: Tuple = ()) -> int:
        set_clause = ", ".join([f"{k}=?" for k in data.keys()])
        sql = f"UPDATE {self.table} SET {set_clause} WHERE {where}"
        cur = self.execute(sql, tuple(data.values()) + params)
        return cur.rowcount

    def delete(self, where: str, params: Tuple = ()) -> int:
        sql = f"DELETE FROM {self.table} WHERE {where}"
        cur = self.execute(sql, params)
        return cur.rowcount

    def count(self, where: str = "", params: Tuple = ()) -> int:
        sql = f"SELECT COUNT(*) AS c FROM {self.table}"
        if where:
            sql += f" WHERE {where}"
        row = self.fetchone(sql, params)
        return row["c"] if row else 0
