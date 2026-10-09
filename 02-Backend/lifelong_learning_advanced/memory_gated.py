from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class MemoryGateConfig:
    novelty_threshold: float = 0.5
    importance_threshold: float = 0.3
    capacity: int = 500


@dataclass
class MemoryEntry:
    key: str
    embedding: np.ndarray
    importance: float = 1.0
    novelty: float = 1.0
    access_count: int = 0
    last_accessed: float = field(default_factory=lambda: 0.0)


class MemoryGated:
    def __init__(self, config: Optional[MemoryGateConfig] = None) -> None:
        self.config = config if config is not None else MemoryGateConfig()
        self._memories: Dict[str, MemoryEntry] = {}
        self._stats: Dict[str, Any] = {"admitted": 0, "rejected_novelty": 0, "rejected_importance": 0}

    def _compute_novelty(self, embedding: np.ndarray) -> float:
        if not self._memories:
            return 1.0
        keys = list(self._memories.keys())
        stored = np.array([self._memories[k].embedding for k in keys])
        norms = np.linalg.norm(stored, axis=1, keepdims=True)
        norm_e = np.linalg.norm(embedding)
        if norm_e == 0:
            return 0.0
        similarities = (stored @ embedding) / (norms.flatten() * norm_e + 1e-12)
        max_sim = float(np.max(similarities))
        return float(max(0.0, 1.0 - max_sim))

    def admit(self, key: str, embedding: np.ndarray, importance: float = 1.0) -> Dict[str, Any]:
        novelty = self._compute_novelty(embedding)
        if novelty < self.config.novelty_threshold:
            self._stats["rejected_novelty"] += 1
            return {"admitted": False, "reason": "low_novelty", "novelty": novelty}
        if importance < self.config.importance_threshold:
            self._stats["rejected_importance"] += 1
            return {"admitted": False, "reason": "low_importance", "novelty": novelty, "importance": importance}
        if len(self._memories) >= self.config.capacity and key not in self._memories:
            self._forget_weakest()
        entry = MemoryEntry(key=key, embedding=embedding.copy(), importance=importance, novelty=novelty)
        self._memories[key] = entry
        self._stats["admitted"] += 1
        return {"admitted": True, "novelty": novelty, "importance": importance}

    def access(self, key: str) -> Optional[MemoryEntry]:
        if key not in self._memories:
            return None
        entry = self._memories[key]
        entry.access_count += 1
        entry.last_accessed = float(np.sum(entry.embedding))
        return entry

    def _forget_weakest(self) -> None:
        if not self._memories:
            return
        weakest = min(self._memories.values(), key=lambda m: m.importance * m.novelty + m.access_count * 0.1)
        del self._memories[weakest.key]

    def query(self, embedding: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        if not self._memories:
            return []
        keys = list(self._memories.keys())
        stored = np.array([self._memories[k].embedding for k in keys])
        norm_e = np.linalg.norm(embedding)
        if norm_e == 0:
            return []
        norms = np.linalg.norm(stored, axis=1, keepdims=True)
        sims = (stored @ embedding) / (norms.flatten() * norm_e + 1e-12)
        idx = np.argsort(sims)[::-1][:top_k]
        return [(keys[i], float(sims[i])) for i in idx]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "capacity": self.config.capacity,
            "used": len(self._memories),
            "admitted": self._stats["admitted"],
            "rejected_novelty": self._stats["rejected_novelty"],
            "rejected_importance": self._stats["rejected_importance"],
        }
