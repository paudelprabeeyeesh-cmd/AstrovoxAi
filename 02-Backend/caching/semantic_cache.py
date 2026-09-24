import hashlib
from typing import Any, Dict, Optional

import numpy as np


class SemanticCache:
    def __init__(self, max_entries: int = 1024, similarity_threshold: float = 0.9):
        self.max_entries = max_entries
        self.similarity_threshold = similarity_threshold
        self._store: Dict[str, Any] = {}
        self._embeddings: Dict[str, np.ndarray] = {}

    def _embed(self, text: str) -> np.ndarray:
        h = hashlib.sha256(text.encode()).digest()
        arr = np.frombuffer(h, dtype=np.uint8).astype(np.float32)
        arr = arr / (np.linalg.norm(arr) + 1e-8)
        return arr

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def set(self, key: str, value: Any, text: str) -> None:
        self._evict_if_needed()
        self._store[key] = value
        self._embeddings[key] = self._embed(text)

    def get(self, text: str) -> Optional[Any]:
        if not self._store:
            return None
        query = self._embed(text)
        best_key = None
        best_score = -1.0
        for key, emb in self._embeddings.items():
            score = self._cosine_similarity(query, emb)
            if score > best_score:
                best_score = score
                best_key = key
        if best_key is not None and best_score >= self.similarity_threshold:
            return self._store[best_key]
        return None

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            self._embeddings.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        self._store.clear()
        self._embeddings.clear()

    def _evict_if_needed(self) -> None:
        while len(self._store) >= self.max_entries:
            if not self._store:
                break
            oldest = next(iter(self._store))
            del self._store[oldest]
            self._embeddings.pop(oldest, None)

    def stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._store),
            "max_entries": self.max_entries,
            "similarity_threshold": self.similarity_threshold,
        }
