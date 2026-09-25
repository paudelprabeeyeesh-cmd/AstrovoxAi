from typing import Optional, Dict, Any, List, Tuple
import hashlib
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SemanticCacheEntry:
    query: str
    query_embedding: Optional[List[float]]
    results: List[Dict[str, Any]]
    created_at: float
    hit_count: int = 0
    ttl: float = 3600.0


class SemanticCache:
    def __init__(self, max_size: int = 10000, similarity_threshold: float = 0.92, default_ttl: float = 3600.0):
        self._entries: Dict[str, SemanticCacheEntry] = {}
        self._order: List[str] = []
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.default_ttl = default_ttl

    def _compute_key(self, query: str) -> str:
        return hashlib.sha256(query.encode('utf-8')).hexdigest()

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def get(self, query: str, query_embedding: Optional[List[float]] = None) -> Optional[List[Dict[str, Any]]]:
        self._cleanup_expired()
        if query_embedding:
            for key, entry in self._entries.items():
                if entry.query_embedding:
                    sim = self._cosine_similarity(query_embedding, entry.query_embedding)
                    if sim >= self.similarity_threshold:
                        entry.hit_count += 1
                        logger.debug("Semantic cache hit (similarity=%.3f) for query: %s", sim, query)
                        return entry.results
        key = self._compute_key(query)
        entry = self._entries.get(key)
        if entry:
            entry.hit_count += 1
            logger.debug("Exact cache hit for query: %s", query)
            return entry.results
        return None

    def set(self, query: str, results: List[Dict[str, Any]], query_embedding: Optional[List[float]] = None, ttl: Optional[float] = None) -> None:
        self._cleanup_expired()
        key = self._compute_key(query)
        entry = SemanticCacheEntry(
            query=query,
            query_embedding=query_embedding,
            results=results,
            created_at=time.time(),
            ttl=ttl or self.default_ttl,
        )
        if key in self._entries:
            self._entries[key] = entry
        else:
            if len(self._entries) >= self.max_size:
                self._evict()
            self._entries[key] = entry
            self._order.append(key)
        logger.debug("Cached results for query: %s", query)

    def invalidate(self, query: str) -> bool:
        key = self._compute_key(query)
        if key in self._entries:
            del self._entries[key]
            if key in self._order:
                self._order.remove(key)
            return True
        return False

    def clear(self) -> None:
        self._entries.clear()
        self._order.clear()

    def _evict(self) -> None:
        if not self._order:
            return
        oldest_key = self._order.pop(0)
        self._entries.pop(oldest_key, None)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._entries.items() if now - v.created_at > v.ttl]
        for key in expired_keys:
            self._entries.pop(key, None)
            if key in self._order:
                self._order.remove(key)

    def stats(self) -> Dict[str, Any]:
        total_hits = sum(e.hit_count for e in self._entries.values())
        return {
            'size': len(self._entries),
            'max_size': self.max_size,
            'total_hits': total_hits,
            'hit_rate': total_hits / max(len(self._entries), 1),
        }
