from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ReplaySample:
    x: np.ndarray
    y: np.ndarray
    task_id: str = "task"


class ReplayBuffer:
    def __init__(self, capacity: int = 500) -> None:
        self.capacity = capacity
        self._buffer: List[ReplaySample] = []

    def add(self, x: np.ndarray, y: np.ndarray, task_id: str = "task") -> None:
        sample = ReplaySample(x=x.copy(), y=y.copy(), task_id=task_id)
        self._buffer.append(sample)
        if len(self._buffer) > self.capacity:
            self._buffer = self._buffer[-self.capacity :]

    def add_batch(self, x: np.ndarray, y: np.ndarray, task_id: str = "task") -> None:
        for i in range(len(x)):
            self.add(x[i], y[i], task_id=task_id)

    def sample(self, batch_size: int) -> Tuple[np.ndarray, np.ndarray]:
        if not self._buffer:
            raise ValueError("ReplayBuffer is empty")
        indices = np.random.choice(len(self._buffer), size=min(batch_size, len(self._buffer)), replace=False)
        batch = [self._buffer[i] for i in indices]
        x_batch = np.array([s.x for s in batch])
        y_batch = np.array([s.y for s in batch])
        return x_batch, y_batch

    def sample_task(self, task_id: str, batch_size: int) -> Tuple[np.ndarray, np.ndarray]:
        task_samples = [s for s in self._buffer if s.task_id == task_id]
        if not task_samples:
            raise ValueError(f"No samples found for task {task_id}")
        indices = np.random.choice(len(task_samples), size=min(batch_size, len(task_samples)), replace=False)
        batch = [task_samples[i] for i in indices]
        x_batch = np.array([s.x for s in batch])
        y_batch = np.array([s.y for s in batch])
        return x_batch, y_batch

    def __len__(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer = []

    def stats(self) -> Dict[str, Any]:
        task_counts: Dict[str, int] = {}
        for s in self._buffer:
            task_counts[s.task_id] = task_counts.get(s.task_id, 0) + 1
        return {
            "total": len(self._buffer),
            "capacity": self.capacity,
            "tasks": task_counts,
        }
