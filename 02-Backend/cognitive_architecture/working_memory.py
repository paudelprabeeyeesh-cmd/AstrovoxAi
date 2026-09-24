import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MemoryChunk:
    content: Any
    salience: float
    timestamp: float
    decay_rate: float = 0.01
    age: float = 0.0

    def get_activation(self) -> float:
        return self.salience * np.exp(-self.decay_rate * self.age)


class WorkingMemoryBuffer:
    def __init__(self, capacity: int = 7, decay_rate: float = 0.01):
        self.capacity = capacity
        self.decay_rate = decay_rate
        self.chunks: List[MemoryChunk] = []
        self.attended_indices: List[int] = []

    def add(self, content: Any, salience: float, timestamp: float) -> bool:
        if len(self.chunks) >= self.capacity:
            self._evict_lowest()
        chunk = MemoryChunk(
            content=content,
            salience=salience,
            timestamp=timestamp,
            decay_rate=self.decay_rate,
        )
        self.chunks.append(chunk)
        return True

    def _evict_lowest(self) -> None:
        if not self.chunks:
            return
        activations = [c.get_activation() for c in self.chunks]
        min_idx = int(np.argmin(activations))
        self.chunks.pop(min_idx)
        if min_idx in self.attended_indices:
            self.attended_indices.remove(min_idx)

    def attend(self, indices: List[int]) -> List[Any]:
        self.attended_indices = [i for i in indices if 0 <= i < len(self.chunks)]
        return [self.chunks[i].content for i in self.attended_indices]

    def get_activations(self) -> np.ndarray:
        return np.array([c.get_activation() for c in self.chunks])

    def step(self, dt: float = 1.0) -> None:
        for chunk in self.chunks:
            chunk.age += dt

    def capacity_utilization(self) -> float:
        return len(self.chunks) / self.capacity


class AttentionGate:
    def __init__(self, threshold: float = 0.3, top_down_weight: float = 0.7):
        self.threshold = threshold
        self.top_down_weight = top_down_weight
        self.bottom_up_weight = 1.0 - top_down_weight
        self._goal_vector: Optional[np.ndarray] = None

    def set_goal(self, goal_vector: np.ndarray) -> None:
        norm = np.linalg.norm(goal_vector)
        if norm > 0:
            self._goal_vector = goal_vector / norm

    def gate(self, items: List[Any], item_vectors: np.ndarray) -> List[int]:
        if self._goal_vector is None or len(items) == 0:
            return list(range(len(items)))

        similarities = item_vectors @ self._goal_vector
        bottom_up = self._salience_scores(items)
        combined = (
            self.top_down_weight * similarities + self.bottom_up_weight * bottom_up
        )
        passed = np.where(combined > self.threshold)[0].tolist()
        return passed

    def _salience_scores(self, items: List[Any]) -> np.ndarray:
        if len(items) == 0:
            return np.array([])
        return np.ones(len(items)) / len(items)

    def get_attention_allocation(self, items: List[Any], item_vectors: np.ndarray) -> Dict[int, float]:
        passed = self.gate(items, item_vectors)
        if len(passed) == 0:
            return {}
        allocation = {}
        for idx in passed:
            if self._goal_vector is not None and len(item_vectors) > idx:
                allocation[idx] = float(item_vectors[idx] @ self._goal_vector)
            else:
                allocation[idx] = 1.0 / len(passed)
        return allocation


class WorkingMemorySystem:
    def __init__(self, capacity: int = 7, attention_threshold: float = 0.3):
        self.buffer = WorkingMemoryBuffer(capacity=capacity)
        self.gate = AttentionGate(threshold=attention_threshold)
        self._item_registry: List[Any] = []
        self._vector_registry: List[np.ndarray] = []

    def register_item(self, item: Any, vector: np.ndarray) -> int:
        idx = len(self._item_registry)
        self._item_registry.append(item)
        self._vector_registry.append(vector)
        return idx

    def process_input(self, item: Any, vector: np.ndarray, salience: float, timestamp: float) -> bool:
        self._item_registry.append(item)
        self._vector_registry.append(vector)
        passed = self.gate.gate([item], np.array([vector]))
        if passed:
            return self.buffer.add(item, salience, timestamp)
        return False

    def attend(self, indices: List[int]) -> List[Any]:
        return self.buffer.attend(indices)

    def step(self, dt: float = 1.0) -> None:
        self.buffer.step(dt)

    def get_state(self) -> Dict[str, Any]:
        return {
            "contents": [c.content for c in self.buffer.chunks],
            "activations": self.buffer.get_activations().tolist(),
            "attended": self.buffer.attended_indices,
            "capacity_utilization": self.buffer.capacity_utilization(),
        }
