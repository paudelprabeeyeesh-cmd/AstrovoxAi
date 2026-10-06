"""Vector database and embedding index.

Provides an in-memory vector store with approximate nearest-neighbor search,
metadata filtering, and incremental backups. The index is intentionally
simple so it can be reviewed and tested without external services.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    embedding: tuple[float, ...]
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorIndex:
    """Flat vector index with cosine similarity."""

    def __init__(self) -> None:
        self._docs: Dict[str, Document] = {}
        self._vectors: Dict[str, tuple[float, ...]] = {}

    def add(self, doc: Document) -> None:
        self._docs[doc.id] = doc
        self._vectors[doc.id] = doc.embedding

    def add_many(self, docs: Iterable[Document]) -> None:
        for doc in docs:
            self.add(doc)

    def search(self, query: tuple[float, ...], top_k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Tuple[Document, float]]:
        scored: List[Tuple[Document, float]] = []
        q_norm = math.sqrt(sum(x * x for x in query))
        for doc in self._docs.values():
            if metadata_filter:
                if not all(doc.metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue
            vector = self._vectors[doc.id]
            dot = sum(a * b for a, b in zip(query, vector))
            norm = math.sqrt(sum(x * x for x in vector))
            score = dot / max(q_norm * norm, 1e-12)
            scored.append((doc, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def remove(self, doc_id: str) -> None:
        self._docs.pop(doc_id, None)
        self._vectors.pop(doc_id, None)

    def __len__(self) -> int:
        return len(self._docs)


class HybridSearchEngine:
    """Combines vector similarity with keyword metadata filtering."""

    def __init__(self, index: Optional[VectorIndex] = None) -> None:
        self.index = index or VectorIndex()

    def upsert(self, docs: Iterable[Document]) -> None:
        self.index.add_many(docs)

    def query(self, text: str, embedding: tuple[float, ...], top_k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Tuple[Document, float]]:
        return self.index.search(embedding, top_k=top_k, metadata_filter=metadata_filter)


class SnapshotSystem:
    """Point-in-time snapshots for vector data."""

    def __init__(self, directory: str = "snapshots") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, index: VectorIndex) -> Path:
        path = self.directory / f"{name}.json"
        data = {
            "docs": [
                {
                    "id": doc.id,
                    "text": doc.text,
                    "embedding": list(doc.embedding),
                    "metadata": doc.metadata,
                }
                for doc in index._docs.values()
            ]
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def load(self, name: str) -> VectorIndex:
        path = self.directory / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        index = VectorIndex()
        for item in data.get("docs", []):
            index.add(Document(
                id=item["id"],
                text=item["text"],
                embedding=tuple(item["embedding"]),
                metadata=item.get("metadata", {}),
            ))
        return index


class IncrementalBackup:
    """Append-only backup of vector updates."""

    def __init__(self, directory: str = "backups") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._log: List[Dict[str, Any]] = []

    def record(self, operation: str, doc: Document) -> None:
        self._log.append({"op": operation, "doc": {"id": doc.id, "text": doc.text, "embedding": list(doc.embedding), "metadata": doc.metadata}})

    def flush(self, name: str) -> Path:
        path = self.directory / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for entry in self._log:
                f.write(json.dumps(entry) + "\n")
        return path
