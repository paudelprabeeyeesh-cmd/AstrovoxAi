import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import time


@dataclass
class MemoryTrace:
    content: Any
    embedding: np.ndarray
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0
    access_count: int = 0
    decay_rate: float = 0.01
    memory_type: str = "episodic"

    def activation(self) -> float:
        age = time.time() - self.timestamp
        recency = np.exp(-self.decay_rate * age)
        frequency = np.log1p(self.access_count)
        return float(self.importance * (0.5 * recency + 0.5 * frequency))


class EpisodicMemory:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.traces: Dict[str, MemoryTrace] = {}
        self._episode_counter = 0

    def encode(self, content: Any, embedding: Optional[np.ndarray] = None, importance: float = 1.0) -> str:
        self._episode_counter += 1
        trace_id = f"ep_{self._episode_counter}"
        if embedding is None:
            embedding = np.random.randn(16)
        self.traces[trace_id] = MemoryTrace(
            content=content,
            embedding=embedding,
            importance=importance,
            memory_type="episodic",
        )
        if len(self.traces) > self.capacity:
            self._forget_weakest()
        return trace_id

    def retrieve(self, cue: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        scores = []
        for trace_id, trace in self.traces.items():
            sim = self._cosine_similarity(cue, trace.embedding)
            act = trace.activation()
            score = 0.7 * sim + 0.3 * act
            scores.append((trace_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        results = scores[:top_k]
        for trace_id, _ in results:
            self.traces[trace_id].access_count += 1
        return results

    def _forget_weakest(self) -> None:
        if not self.traces:
            return
        weakest_id = min(self.traces.keys(), key=lambda k: self.traces[k].activation())
        del self.traces[weakest_id]

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))


class SemanticMemory:
    def __init__(self, dim: int = 16):
        self.dim = dim
        self.concepts: Dict[str, np.ndarray] = {}
        self._relations: Dict[str, List[Tuple[str, str]]] = {}

    def add_concept(self, name: str, embedding: Optional[np.ndarray] = None) -> None:
        if embedding is None:
            embedding = np.random.randn(self.dim) * 0.1
        self.concepts[name] = embedding

    def relate(self, concept_a: str, relation: str, concept_b: str) -> None:
        if relation not in self._relations:
            self._relations[relation] = []
        self._relations[relation].append((concept_a, concept_b))

    def get_related(self, concept: str, relation: str) -> List[str]:
        return [b for a, b in self._relations.get(relation, []) if a == concept]

    def similarity(self, concept_a: str, concept_b: str) -> float:
        if concept_a not in self.concepts or concept_b not in self.concepts:
            return 0.0
        a, b = self.concepts[concept_a], self.concepts[concept_b]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))


class WorkingMemoryStore:
    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.slots: List[Dict[str, Any]] = []

    def store(self, item: Any, salience: float) -> bool:
        if len(self.slots) >= self.capacity:
            self._evict()
        self.slots.append({"content": item, "salience": salience, "timestamp": time.time()})
        return True

    def _evict(self) -> None:
        if not self.slots:
            return
        min_idx = int(np.argmin([s["salience"] for s in self.slots]))
        self.slots.pop(min_idx)

    def get_contents(self) -> List[Any]:
        return [s["content"] for s in self.slots]

    def step(self, dt: float = 1.0) -> None:
        for slot in self.slots:
            slot["age"] = slot.get("age", 0.0) + dt
            slot["salience"] *= np.exp(-0.01 * dt)


class MemorySystem:
    def __init__(self, capacity: int = 1000, working_capacity: int = 7):
        self.episodic = EpisodicMemory(capacity=capacity)
        self.semantic = SemanticMemory()
        self.working = WorkingMemoryStore(capacity=working_capacity)
        self._consolidation_log: List[Dict[str, Any]] = []

    def encode(self, content: Any, embedding: Optional[np.ndarray] = None, importance: float = 1.0) -> str:
        trace_id = self.episodic.encode(content, embedding=embedding, importance=importance)
        self.working.store(content, salience=importance)
        return trace_id

    def retrieve(self, cue: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        return self.episodic.retrieve(cue, top_k=top_k)

    def consolidate(self) -> Dict[str, Any]:
        recent = sorted(
            self.episodic.traces.values(),
            key=lambda t: t.activation(),
            reverse=True,
        )[:10]
        for trace in recent:
            name = f"concept_{hash(str(trace.content)) % 10000}"
            self.semantic.add_concept(name, embedding=trace.embedding)
        entry = {
            "timestamp": time.time(),
            "consolidated": len(recent),
        }
        self._consolidation_log.append(entry)
        return entry

    def get_status(self) -> Dict[str, Any]:
        return {
            "episodic_size": len(self.episodic.traces),
            "semantic_concepts": len(self.semantic.concepts),
            "working_memory_load": len(self.working.slots),
            "consolidations": len(self._consolidation_log),
        }
