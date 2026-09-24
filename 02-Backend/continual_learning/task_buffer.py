import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from heapq import heappush, heappop
from .catastrophic_forgetting_prevention import ReplayBuffer


class TaskBuffer:
    def __init__(
        self,
        buffer_size: int = 5000,
        per_task_capacity: Optional[int] = None,
        priority_alpha: float = 0.6
    ):
        self.buffer_size = buffer_size
        self.per_task_capacity = per_task_capacity or buffer_size
        self.priority_alpha = priority_alpha
        self.samples: List[Tuple[str, Dict[str, np.ndarray], float]] = []
        self.task_counts: Dict[str, int] = {}
        self.task_heap: List[Tuple[float, int, str]] = []
        self._counter = 0

    def store_sample(
        self,
        task_id: str,
        sample: Dict[str, np.ndarray],
        priority: float = 1.0
    ) -> None:
        if task_id not in self.task_counts:
            self.task_counts[task_id] = 0

        if self.task_counts[task_id] >= self.per_task_capacity:
            self._purge_oldest_task_sample(task_id)

        scaled_priority = -priority ** self.priority_alpha
        self._counter += 1
        heappush(self.task_heap, (scaled_priority, self._counter, task_id))
        self.samples.append((task_id, sample, priority))
        self.task_counts[task_id] += 1

        self._enforce_global_capacity()

    def _purge_oldest_task_sample(self, task_id: str) -> None:
        for i in range(len(self.samples) - 1, -1, -1):
            if self.samples[i][0] == task_id:
                self.samples.pop(i)
                self.task_counts[task_id] -= 1
                break

    def _enforce_global_capacity(self) -> None:
        while len(self.samples) > self.buffer_size:
            _, _, removed_task = heappop(self.task_heap)
            for i in range(len(self.samples) - 1, -1, -1):
                if self.samples[i][0] == removed_task:
                    self.samples.pop(i)
                    if removed_task in self.task_counts:
                        self.task_counts[removed_task] = max(
                            0, self.task_counts[removed_task] - 1
                        )
                    break

    def sample(
        self,
        n: int,
        task_id: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, np.ndarray]]]:
        if task_id is not None:
            candidates = [
                (tid, s) for tid, s, _ in self.samples if tid == task_id
            ]
        else:
            candidates = [(tid, s) for tid, s, _ in self.samples]

        if not candidates:
            return []

        size = min(n, len(candidates))
        indices = np.random.choice(len(candidates), size=size, replace=False)
        return [candidates[i] for i in indices]

    def balanced_sample(
        self,
        n: int,
        task_ids: Optional[List[str]] = None
    ) -> Dict[str, List[Tuple[str, Dict[str, np.ndarray]]]]:
        active_tasks = task_ids or list(self.task_counts.keys())
        if not active_tasks:
            return {}

        per_task = max(n // len(active_tasks), 1)
        remainder = n - per_task * len(active_tasks)

        result: Dict[str, List[Tuple[str, Dict[str, np.ndarray]]]] = {}
        for idx, task_id in enumerate(active_tasks):
            count = per_task + (1 if idx < remainder else 0)
            result[task_id] = self.sample(count, task_id=task_id)

        return result

    def get_task_distribution(self) -> Dict[str, float]:
        total = sum(self.task_counts.values())
        if total == 0:
            return {}
        return {tid: count / total for tid, count in self.task_counts.items()}

    def get_stats(self) -> Dict[str, Any]:
        total = sum(self.task_counts.values())
        return {
            "total_samples": total,
            "buffer_size": self.buffer_size,
            "utilization": total / self.buffer_size if self.buffer_size > 0 else 0.0,
            "num_tasks": len(self.task_counts),
            "task_counts": dict(self.task_counts),
            "task_distribution": self.get_task_distribution()
        }

    def __len__(self) -> int:
        return len(self.samples)
