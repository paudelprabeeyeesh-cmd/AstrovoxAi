from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    id: str
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "embedding": self.embedding,
        }


class StorageBackend(ABC):
    @abstractmethod
    def save(self, entry: MemoryEntry) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self, entry_id: str) -> MemoryEntry | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, entry_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_entries(self) -> list[MemoryEntry]:
        raise NotImplementedError


class FileStorage(StorageBackend):
    def __init__(self, storage_dir: str) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, entry_id: str) -> Path:
        return self.storage_dir / f"{entry_id}.json"

    def save(self, entry: MemoryEntry) -> None:
        path = self._path(entry.id)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entry.to_dict(), fh)

    def load(self, entry_id: str) -> MemoryEntry | None:
        path = self._path(entry_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return MemoryEntry(**data)

    def delete(self, entry_id: str) -> None:
        path = self._path(entry_id)
        if path.exists():
            path.unlink()

    def list_entries(self) -> list[MemoryEntry]:
        entries: list[MemoryEntry] = []
        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                entries.append(MemoryEntry(**data))
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(entries, key=lambda e: e.timestamp)


class InMemoryStorage(StorageBackend):
    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}

    def save(self, entry: MemoryEntry) -> None:
        self._entries[entry.id] = entry

    def load(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)

    def delete(self, entry_id: str) -> None:
        self._entries.pop(entry_id, None)

    def list_entries(self) -> list[MemoryEntry]:
        return sorted(self._entries.values(), key=lambda e: e.timestamp)


class AgentMemory:
    def __init__(self, storage: StorageBackend | None = None) -> None:
        self.storage = storage or InMemoryStorage()

    def store(self, content: Any, metadata: dict[str, Any] | None = None, entry_id: str | None = None) -> MemoryEntry:
        if entry_id is None:
            entry_id = f"mem_{int(time.time() * 1000)}_{hash(str(content)) % 10000}"
        entry = MemoryEntry(id=entry_id, content=content, metadata=metadata or {})
        self.storage.save(entry)
        return entry

    def recall(self, entry_id: str) -> MemoryEntry | None:
        return self.storage.load(entry_id)

    def forget(self, entry_id: str) -> None:
        self.storage.delete(entry_id)

    def search(self, query: str, top_k: int = 10) -> list[MemoryEntry]:
        results: list[tuple[float, MemoryEntry]] = []
        query_lower = query.lower()
        for entry in self.storage.list_entries():
            score = self._similarity(query_lower, entry)
            if score > 0:
                results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:top_k]]

    def _similarity(self, query: str, entry: MemoryEntry) -> float:
        content = str(entry.content).lower()
        metadata = json.dumps(entry.metadata).lower()
        combined = content + " " + metadata
        query_terms = query.split()
        score = 0.0
        for term in query_terms:
            if term in combined:
                score += 1.0
        return score / max(len(query_terms), 1)

    def list_all(self) -> list[MemoryEntry]:
        return self.storage.list_entries()
