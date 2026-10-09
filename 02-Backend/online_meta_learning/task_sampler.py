import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
import random


@dataclass
class TaskSpec:
    task_id: str
    input_dim: int
    output_dim: int
    num_samples: int = 20
    noise_scale: float = 0.1
    seed: Optional[int] = None


class TaskSampler:
    def __init__(self, base_input_dim: int = 8, base_output_dim: int = 4):
        self.base_input_dim = base_input_dim
        self.base_output_dim = base_output_dim
        self.task_registry: Dict[str, TaskSpec] = {}
        self.task_stats: Dict[str, Dict[str, Any]] = {}
        self._next_id = 0

    def register_task(
        self,
        task_id: str,
        input_dim: Optional[int] = None,
        output_dim: Optional[int] = None,
        num_samples: int = 20,
        noise_scale: float = 0.1,
        seed: Optional[int] = None
    ) -> TaskSpec:
        spec = TaskSpec(
            task_id=task_id,
            input_dim=input_dim if input_dim is not None else self.base_input_dim,
            output_dim=output_dim if output_dim is not None else self.base_output_dim,
            num_samples=num_samples,
            noise_scale=noise_scale,
            seed=seed,
        )
        self.task_registry[task_id] = spec
        self.task_stats[task_id] = {'sampled': 0, 'total_samples': 0}
        return spec

    def sample(self, task_id: str) -> Tuple[np.ndarray, np.ndarray]:
        if task_id not in self.task_registry:
            raise KeyError(f"Unknown task_id: {task_id}")
        spec = self.task_registry[task_id]
        rng = np.random.RandomState(spec.seed)
        x = rng.randn(spec.num_samples, spec.input_dim).astype(np.float64)
        y = rng.randn(spec.num_samples, spec.output_dim).astype(np.float64) * spec.noise_scale
        self.task_stats[task_id]['sampled'] += 1
        self.task_stats[task_id]['total_samples'] += spec.num_samples
        return x, y

    def sample_batch(
        self,
        task_ids: List[str],
        samples_per_task: Optional[int] = None
    ) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        result: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        for tid in task_ids:
            spec = self.task_registry.get(tid)
            if spec is None:
                raise KeyError(f"Unknown task_id: {tid}")
            n = samples_per_task if samples_per_task is not None else spec.num_samples
            rng = np.random.RandomState(spec.seed)
            x = rng.randn(n, spec.input_dim).astype(np.float64)
            y = rng.randn(n, spec.output_dim).astype(np.float64) * spec.noise_scale
            self.task_stats[tid]['sampled'] += 1
            self.task_stats[tid]['total_samples'] += n
            result[tid] = (x, y)
        return result

    def sample_random(self, num_tasks: int = 1) -> List[Tuple[str, np.ndarray, np.ndarray]]:
        if not self.task_registry:
            raise RuntimeError("No tasks registered")
        results: List[Tuple[str, np.ndarray, np.ndarray]] = []
        for _ in range(num_tasks):
            tid = random.choice(list(self.task_registry.keys()))
            x, y = self.sample(tid)
            results.append((tid, x, y))
        return results

    def get_task_distribution(self) -> Dict[str, float]:
        counts = {tid: st['sampled'] for tid, st in self.task_stats.items()}
        total = sum(counts.values())
        if total == 0:
            return {}
        return {tid: c / total for tid, c in counts.items()}

    def get_report(self) -> Dict[str, Any]:
        return {
            'num_registered': len(self.task_registry),
            'task_ids': list(self.task_registry.keys()),
            'distribution': self.get_task_distribution(),
            'task_stats': dict(self.task_stats),
        }
