"""Distributed memory: hot / warm / cold tiers + vector / semantic layers."""

from __future__ import annotations

import hashlib
import time
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import make_id, now


class MemoryTier(str, Enum):
    HOT = "hot"        # in-process dict
    WARM = "warm"      # pluggable SQL/Redis
    COLD = "cold"      # pluggable S3/object storage
    VECTOR = "vector"  # pluggable vector DB
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    WORKSPACE = "workspace"
    AGENT = "agent"


@dataclass
class MemoryRecord:
    key: str
    value: Any
    tier: MemoryTier
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)
    expires_at: Optional[float] = None
    compressed: bool = False
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._hash()

    def _hash(self) -> str:
        try:
            if isinstance(self.value, (bytes, bytearray)):
                payload = bytes(self.value)
            else:
                payload = repr(self.value).encode("utf-8")
        except Exception:
            payload = b""
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "tier": self.tier.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "compressed": self.compressed,
            "version": self.version,
            "metadata": self.metadata,
            "checksum": self.checksum,
            "size": len(repr(self.value)),
        }


class HotStore:
    def __init__(self) -> None:
        self._data: Dict[str, MemoryRecord] = {}

    def put(self, key: str, value: Any, *, tier: MemoryTier = MemoryTier.HOT, ttl: Optional[float] = None, **meta: Any) -> MemoryRecord:
        record = MemoryRecord(
            key=key,
            value=value,
            tier=tier,
            metadata=dict(meta),
            expires_at=(now() + ttl) if ttl else None,
        )
        self._data[key] = record
        return record

    def get(self, key: str) -> Optional[MemoryRecord]:
        record = self._data.get(key)
        if record is None:
            return None
        if record.expires_at and record.expires_at <= now():
            del self._data[key]
            return None
        return record

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def keys(self) -> List[str]:
        return list(self._data.keys())

    def stats(self) -> Dict[str, int]:
        return {"entries": len(self._data)}


class WarmStore:
    """Pluggable warm store; defaults to in-process with simple versioning."""

    def __init__(self) -> None:
        self._data: Dict[str, MemoryRecord] = {}
        self._replicas: Dict[str, List[MemoryRecord]] = {}

    def put(self, record: MemoryRecord, *, replicas: int = 1) -> None:
        self._data[record.key] = record
        if replicas > 0:
            self._replicas[record.key] = [
                MemoryRecord(
                    key=record.key,
                    value=record.value,
                    tier=record.tier,
                    metadata={**record.metadata, "replica": i},
                    version=record.version,
                )
                for i in range(replicas)
            ]

    def get(self, key: str) -> Optional[MemoryRecord]:
        return self._data.get(key)

    def replicas(self, key: str) -> List[MemoryRecord]:
        return list(self._replicas.get(key, []))

    def snapshot(self) -> List[MemoryRecord]:
        return list(self._data.values())

    def restore(self, records: Iterable[MemoryRecord]) -> int:
        count = 0
        for r in records:
            self._data[r.key] = r
            count += 1
        return count


class ColdStore:
    """Object-storage backed cold store; defaults to an in-process blob map."""

    def __init__(self) -> None:
        self._blobs: Dict[str, bytes] = {}
        self._index: Dict[str, str] = {}  # key -> blob id

    def put(self, key: str, value: Any, *, compress: bool = True) -> str:
        if isinstance(value, str):
            payload = value.encode("utf-8")
        elif isinstance(value, (bytes, bytearray)):
            payload = bytes(value)
        else:
            payload = repr(value).encode("utf-8")
        if compress:
            payload = zlib.compress(payload)
        blob_id = make_id("blob")
        self._blobs[blob_id] = payload
        self._index[key] = blob_id
        return blob_id

    def get(self, key: str) -> Optional[bytes]:
        blob_id = self._index.get(key)
        if not blob_id:
            return None
        payload = self._blobs.get(blob_id)
        if payload is None:
            return None
        try:
            return zlib.decompress(payload)
        except zlib.error:
            return payload

    def delete(self, key: str) -> bool:
        blob_id = self._index.pop(key, None)
        if blob_id is None:
            return False
        self._blobs.pop(blob_id, None)
        return True

    def stats(self) -> Dict[str, int]:
        return {"blobs": len(self._blobs), "indexed_keys": len(self._index)}


class VectorIndex:
    """In-process vector index for prototype and tests.

    Uses numpy when available, otherwise falls back to a pure Python
    implementation with cosine similarity.
    """

    def __init__(self) -> None:
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def upsert(self, key: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        self._vectors[key] = list(vector)
        self._metadata[key] = metadata or {}

    def delete(self, key: str) -> bool:
        if key in self._vectors:
            del self._vectors[key]
            self._metadata.pop(key, None)
            return True
        return False

    def search(self, query: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        scored: List[Tuple[str, float, Dict[str, Any]]] = []
        for key, vec in self._vectors.items():
            score = _cosine(query, vec)
            scored.append((key, score, self._metadata.get(key, {})))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def size(self) -> int:
        return len(self._vectors)


def _cosine(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(n):
        dot += a[i] * b[i]
        na += a[i] * a[i]
        nb += b[i] * b[i]
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb) ** 0.5


class MemoryManager:
    """Coordinates hot/warm/cold/vector tiers with promotion logic."""

    def __init__(self) -> None:
        self.hot = HotStore()
        self.warm = WarmStore()
        self.cold = ColdStore()
        self.vector = VectorIndex()
        self._dedup_index: Dict[str, str] = {}  # checksum -> key

    # ---- CRUD across tiers -----------------------------------------

    def put(
        self,
        key: str,
        value: Any,
        *,
        tier: MemoryTier = MemoryTier.HOT,
        ttl: Optional[float] = None,
        compress: bool = False,
        **meta: Any,
    ) -> MemoryRecord:
        record = MemoryRecord(
            key=key,
            value=value,
            tier=tier,
            metadata=meta,
            expires_at=(now() + ttl) if ttl else None,
            compressed=compress,
        )
        if record.checksum in self._dedup_index and self._dedup_index[record.checksum] != key:
            existing = self.hot.get(self._dedup_index[record.checksum])
            if existing is not None:
                existing.version += 1
                existing.updated_at = now()
                return existing
        self._dedup_index[record.checksum] = key
        if tier == MemoryTier.HOT:
            self.hot.put(key, value, ttl=ttl, **meta)
        elif tier == MemoryTier.WARM:
            self.warm.put(record)
        elif tier == MemoryTier.COLD:
            self.cold.put(key, value, compress=compress)
        return record

    def get(self, key: str) -> Optional[MemoryRecord]:
        for store in (self.hot, self.warm):
            record = store.get(key)
            if record is not None:
                return record
        if self.cold.get(key) is not None:
            return MemoryRecord(key=key, value=self.cold.get(key), tier=MemoryTier.COLD)
        return None

    def promote(self, key: str, target: MemoryTier) -> Optional[MemoryRecord]:
        record = self.get(key)
        if record is None:
            return None
        if target == MemoryTier.HOT:
            return self.hot.put(key, record.value)
        if target == MemoryTier.WARM:
            warm_record = MemoryRecord(key=key, value=record.value, tier=MemoryTier.WARM)
            self.warm.put(warm_record)
            return warm_record
        if target == MemoryTier.COLD:
            self.cold.put(key, record.value)
            return MemoryRecord(key=key, value=record.value, tier=MemoryTier.COLD)
        return record

    def snapshot(self) -> Dict[str, Any]:
        return {
            "hot": self.hot.stats(),
            "warm": {"entries": len(self.warm.snapshot())},
            "cold": self.cold.stats(),
            "vector": {"size": self.vector.size()},
        }


_GLOBAL_MEMORY: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _GLOBAL_MEMORY
    if _GLOBAL_MEMORY is None:
        _GLOBAL_MEMORY = MemoryManager()
    return _GLOBAL_MEMORY