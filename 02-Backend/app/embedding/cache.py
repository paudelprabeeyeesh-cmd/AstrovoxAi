"""Embedding Cache — prevents duplicate embedding requests."""

import hashlib
import json
import time
from typing import Optional

from .providers import EmbeddingVector


class EmbeddingCache:
    """Cache for embedding results to avoid redundant API calls."""

    def __init__(self, ttl: int = 3600):
        self._cache: dict[str, tuple[EmbeddingVector, float]] = {}
        self._ttl = ttl

    def _make_key(self, text: str, model: str, provider: str) -> str:
        """Create a deterministic cache key."""
        content = f"{provider}:{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model: str, provider: str) -> Optional[EmbeddingVector]:
        """Retrieve a cached embedding."""
        key = self._make_key(text, model, provider)
        entry = self._cache.get(key)
        if entry is None:
            return None
        vector, timestamp = entry
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None
        return vector

    def set(self, text: str, model: str, provider: str, vector: EmbeddingVector):
        """Cache an embedding result."""
        key = self._make_key(text, model, provider)
        self._cache[key] = (vector, time.time())

    def get_many(self, texts: list[str], model: str, provider: str) -> tuple[list[EmbeddingVector], list[str]]:
        """Get cached embeddings, return (found, missing_texts)."""
        found = []
        missing = []
        for text in texts:
            cached = self.get(text, model, provider)
            if cached:
                found.append(cached)
            else:
                missing.append(text)
        return found, missing

    def invalidate(self, text: str, model: str, provider: str):
        """Remove a specific entry from cache."""
        key = self._make_key(text, model, provider)
        self._cache.pop(key, None)

    def clear(self):
        """Clear all cached embeddings."""
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
