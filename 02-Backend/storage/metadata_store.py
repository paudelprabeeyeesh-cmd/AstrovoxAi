import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Union


class MetadataStore:
    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)"
        )
        self._conn.commit()

    def set(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        self._conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        cur = self._conn.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        row = cur.fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM metadata WHERE key = ?", (key,))
        self._conn.commit()

    def exists(self, key: str) -> bool:
        cur = self._conn.execute(
            "SELECT COUNT(1) FROM metadata WHERE key = ?", (key,)
        )
        return cur.fetchone()[0] > 0

    def all(self) -> Dict[str, Any]:
        cur = self._conn.execute("SELECT key, value FROM metadata")
        return {row["key"]: json.loads(row["value"]) for row in cur.fetchall()}

    def close(self) -> None:
        self._conn.close()
