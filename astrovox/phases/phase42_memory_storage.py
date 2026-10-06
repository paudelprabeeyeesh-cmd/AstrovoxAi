"""Persistent memory storage backed by SQLite with JSON fallback."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MemoryStore:
    """Persistent key-value memory store (SQLite, JSON fallback)."""

    path: str = "data/memories.sqlite"

    def __post_init__(self):
        self._path = Path(self.path)
        self._use_json = not self._path.suffix.lower().endswith(".sqlite")
        if self._use_json:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        if not self._use_json and self._path.exists():
            return
        conn = sqlite3.connect(self._path)
        conn.execute("""CREATE TABLE IF NOT EXISTS memories (
            key TEXT PRIMARY KEY, value TEXT, entry_type TEXT,
            created REAL, last_accessed REAL, importance REAL, tags TEXT)""")
        conn.commit()
        conn.close()

    def _load(self) -> dict:
        if self._use_json:
            try:
                return json.loads(self._path.read_text())
            except Exception:
                return {}
        conn = sqlite3.connect(self._path)
        cur = conn.execute("SELECT key, value FROM memories")
        data = {row[0]: row[1] for row in cur.fetchall()}
        conn.close()
        return data

    def _save(self, data: dict) -> None:
        if self._use_json:
            self._path.write_text(json.dumps(data))
            return
        conn = sqlite3.connect(self._path)
        conn.executemany(
            "INSERT OR REPLACE INTO memories (key, value, entry_type, created, last_accessed, importance, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(k, v, "", time.time(), time.time(), 1.0, "") for k, v in data.items()])
        conn.commit()
        conn.close()

    def set(self, key: str, value: Any, entry_type: str = "episodic",
            tags: list[str] | None = None, importance: float = 1.0, ttl: float | None = None) -> str:
        data = self._load()
        row = {
            "key": key,
            "value": json.dumps(value),
            "entry_type": entry_type,
            "tags": ",".join(tags or []),
            "importance": importance,
            "created": time.time(),
            "last_accessed": time.time(),
        }
        if ttl is not None:
            row["expires"] = time.time() + ttl
        data[key] = json.dumps(row)
        self._save(data)
        return key

    def get(self, key: str) -> Any | None:
        data = self._load()
        s = data.get(key)
        if s is None:
            return None
        row = json.loads(s) if isinstance(s, str) else s
        row["last_accessed"] = time.time()
        return row.get("value")

    def delete(self, key: str) -> bool:
        data = self._load()
        if key in data:
            del data[key]
            self._save(data)
            return True
        return False

    def list_keys(self) -> list[str]:
        return list(self._load().keys())

    def count(self) -> int:
        return len(self._load())

    def clear(self) -> None:
        self._save({})

    def search(self, query: str, limit: int = 20) -> list[dict]:
        data = self._load()
        q = query.lower()
        results = []
        for k, s in data.items():
            payload = json.loads(s) if isinstance(s, str) else s
            text = str(payload.get("value")) + " " + payload.get("tags", "")
            if q in text.lower():
                results.append({"key": k, **payload})
        results.sort(key=lambda r: r.get("importance", 0), reverse=True)
        return results[:limit]
