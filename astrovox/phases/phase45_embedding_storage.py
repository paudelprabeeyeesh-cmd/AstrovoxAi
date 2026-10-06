"""Vector column storage for embeddings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VectorRecord:
    """A stored vector with metadata."""
    id: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)
    created: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> dict:
        return {"id": self.id, "vector": self.vector, "metadata": self.metadata,
                "created": self.created}

    @classmethod
    def from_dict(cls, d: dict) -> "VectorRecord":
        return cls(id=d["id"], vector=d["vector"], metadata=d.get("metadata", {}))


class VectorStorage:
    """Vector storage with a vector column."""

    def __init__(self, path: str = "data/vectors.sqlite", dim: int = 8):
        self.path = path
        self.dim = dim
        self._vectors: dict[str, VectorRecord] = {}
        self._meta: dict[str, dict] = {}
        self._init_db()

    def _init_db(self) -> None:
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, "
                     "vector BLOB, metadata TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS vector_meta (vector_id TEXT, "
                     "key TEXT, value TEXT, PRIMARY KEY (vector_id, key))")
        conn.commit()
        conn.close()
        self._load()

    def _load(self) -> None:
        import sqlite3, pickle
        conn = sqlite3.connect(self.path)
        for row in conn.execute("SELECT id, vector, metadata FROM vectors"):
            vec = pickle.loads(row[1]) if isinstance(row[1], bytes) else row[1]
            meta = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            self._vectors[row[0]] = VectorRecord(id=row[0], vector=vec, metadata=meta)
        conn.close()

    def add(self, vector: list[float], metadata: dict | None = None) -> str:
        """Add a vector."""
        vid = f"v_{len(self._vectors)}"
        rec = VectorRecord(id=vid, vector=vector[:self.dim], metadata=metadata or {})
        self._vectors[vid] = rec
        self._save_rec(rec)
        return vid

    def _save_rec(self, rec: VectorRecord) -> None:
        import sqlite3, pickle
        conn = sqlite3.connect(self.path)
        conn.execute("INSERT OR REPLACE INTO vectors (id, vector, metadata) VALUES (?, ?, ?)",
                     (rec.id, pickle.dumps(rec.vector), json.dumps(rec.metadata)))
        conn.execute("DELETE FROM vector_meta WHERE vector_id = ?", (rec.id,))
        for k, v in rec.metadata.items():
            conn.execute("INSERT INTO vector_meta (vector_id, key, value) VALUES (?, ?, ?)",
                         (rec.id, str(k), json.dumps(v) if not isinstance(v, str) else v))
        conn.commit()
        conn.close()

    def get(self, vid: str) -> VectorRecord | None:
        return self._vectors.get(vid)

    def list_ids(self) -> list[str]:
        return list(self._vectors.keys())

    def count(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.execute("DELETE FROM vectors")
        conn.execute("DELETE FROM vector_meta")
        conn.commit()
        conn.close()
        self._vectors.clear()

    def store_meta(self, vid: str, key: str, value: Any) -> None:
        if vid in self._vectors:
            self._vectors[vid].metadata[key] = value
            self._save_rec(self._vectors[vid])
