import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union


class QueryBuilder:
    def __init__(self, table: str) -> None:
        self.table = table
        self._select = "*"
        self._where: List[str] = []
        self._params: List[Any] = []
        self._order_by: str = ""
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def select(self, columns: Union[str, List[str]]) -> "QueryBuilder":
        if isinstance(columns, list):
            self._select = ", ".join(columns)
        else:
            self._select = columns
        return self

    def where(self, condition: str, *params: Any) -> "QueryBuilder":
        self._where.append(condition)
        self._params.extend(params)
        return self

    def order_by(self, column: str, direction: str = "ASC") -> "QueryBuilder":
        self._order_by = f" ORDER BY {column} {direction}"
        return self

    def limit(self, count: int) -> "QueryBuilder":
        self._limit = count
        return self

    def offset(self, count: int) -> "QueryBuilder":
        self._offset = count
        return self

    def build_select(self) -> Tuple[str, List[Any]]:
        sql = f"SELECT {self._select} FROM {self.table}"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        if self._order_by:
            sql += self._order_by
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        return sql, list(self._params)

    def build_insert(self, data: Dict[str, Any]) -> Tuple[str, List[Any]]:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {self.table} ({keys}) VALUES ({placeholders})"
        return sql, list(data.values())

    def build_update(self, data: Dict[str, Any]) -> Tuple[str, List[Any]]:
        set_clause = ", ".join([f"{k}=?" for k in data.keys()])
        sql = f"UPDATE {self.table} SET {set_clause}"
        params = list(data.values())
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
            params.extend(self._params)
        return sql, params

    def build_delete(self) -> Tuple[str, List[Any]]:
        sql = f"DELETE FROM {self.table}"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        return sql, list(self._params)
