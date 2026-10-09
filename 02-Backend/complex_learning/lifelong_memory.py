import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Experience:
    id: str
    content: str
    embedding: List[float]
    timestamp: float
    importance: float = 1.0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


@dataclass
class SemanticFact:
    fact: str
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)


class LifelongMemory:
    def __init__(self, capacity: int = 1000, decay: float = 0.05, consolidation_threshold: int = 3):
        self.capacity = capacity
        self.decay = decay
        self.consolidation_threshold = consolidation_threshold
        self.episodic: Dict[str, Experience] = {}
        self.semantic: Dict[str, SemanticFact] = {}
        self._next_id = 1

    def _generate_id(self) -> str:
        mem_id = f"mem_{self._next_id}"
        self._next_id += 1
        return mem_id

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def store_experience(self, content: str, embedding: List[float], importance: float = 1.0) -> str:
        mem_id = self._generate_id()
        now = time.time()
        exp = Experience(id=mem_id, content=content, embedding=embedding, timestamp=now, importance=importance)
        self.episodic[mem_id] = exp
        self._enforce_capacity()
        return mem_id

    def _enforce_capacity(self) -> None:
        while len(self.episodic) > self.capacity:
            oldest = min(self.episodic.values(), key=lambda e: e.last_accessed)
            del self.episodic[oldest.id]

    def consolidate(self, mem_id: str) -> Optional[str]:
        if mem_id not in self.episodic:
            return None
        exp = self.episodic[mem_id]
        exp.access_count += 1
        exp.last_accessed = time.time()
        if exp.access_count >= self.consolidation_threshold:
            fact_id = f"fact_{mem_id}"
            if fact_id not in self.semantic:
                self.semantic[fact_id] = SemanticFact(fact=exp.content, confidence=0.5, sources=[mem_id])
            else:
                self.semantic[fact_id].confidence = min(1.0, self.semantic[fact_id].confidence + 0.1)
                if mem_id not in self.semantic[fact_id].sources:
                    self.semantic[fact_id].sources.append(mem_id)
            return fact_id
        return None

    def forget_old(self, age_seconds: float) -> int:
        now = time.time()
        to_remove = []
        for mem_id, exp in self.episodic.items():
            if now - exp.timestamp > age_seconds:
                exp.importance *= (1 - self.decay)
                if exp.importance <= 0.01:
                    to_remove.append(mem_id)
        for mem_id in to_remove:
            del self.episodic[mem_id]
        return len(to_remove)

    def retrieve(self, query_embedding: List[float], top_k: int = 5, memory_type: str = "episodic") -> List[Tuple[str, float]]:
        pool = self.episodic if memory_type == "episodic" else {}
        if memory_type == "semantic":
            pool = {k: Experience(id=k, content=v.fact, embedding=[0.0] * len(query_embedding), timestamp=0.0) for k, v in self.semantic.items()}
        scored = []
        for mem_id, exp in pool.items():
            score = self._cosine(query_embedding, exp.embedding)
            scored.append((mem_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def summary(self) -> Dict[str, Any]:
        return {
            "episodic_count": len(self.episodic),
            "semantic_count": len(self.semantic),
            "capacity": self.capacity,
        }
