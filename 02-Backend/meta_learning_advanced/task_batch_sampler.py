import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class TaskSpec:
    task_id: int
    input_dim: int
    output_dim: int
    num_support: int
    num_query: int
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TaskBatchSampler:
    def __init__(self, task_specs: Optional[List[TaskSpec]] = None, seed: Optional[int] = None):
        self.task_specs = task_specs or []
        self.rng = np.random.RandomState(seed)
        self.history: List[TaskSpec] = []

    def add_task_source(self, task_spec: TaskSpec) -> None:
        self.task_specs.append(task_spec)

    def sample_batch(self, batch_size: int, replacement: bool = False) -> List[TaskSpec]:
        if not self.task_specs:
            raise ValueError("No task specs available")
        if replacement:
            indices = self.rng.randint(0, len(self.task_specs), size=batch_size)
        else:
            indices = self.rng.choice(len(self.task_specs), size=min(batch_size, len(self.task_specs)), replace=False)
        batch = [self.task_specs[i] for i in indices]
        self.history.extend(batch)
        return batch

    def sample_stratified(self, batch_size: int, strata_key: str) -> List[TaskSpec]:
        strata: Dict[Any, List[TaskSpec]] = {}
        for spec in self.task_specs:
            key = spec.metadata.get(strata_key)
            strata.setdefault(key, []).append(spec)
        batch = []
        per_stratum = max(1, batch_size // len(strata))
        for key, specs in strata.items():
            n = min(per_stratum, len(specs))
            chosen = self.rng.choice(specs, size=n, replace=False).tolist()
            batch.extend(chosen)
        if len(batch) < batch_size:
            remaining = batch_size - len(batch)
            pool = [s for s in self.task_specs if s not in batch]
            extra = self.rng.choice(pool, size=min(remaining, len(pool)), replace=False).tolist()
            batch.extend(extra)
        self.history.extend(batch)
        return batch

    def generate_task_data(self, spec: TaskSpec) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        x_support = self.rng.randn(spec.num_support, spec.input_dim).astype(np.float64)
        y_support = self.rng.randint(0, spec.output_dim, size=spec.num_support).astype(np.float64)
        x_query = self.rng.randn(spec.num_query, spec.input_dim).astype(np.float64)
        y_query = self.rng.randint(0, spec.output_dim, size=spec.num_query).astype(np.float64)
        return x_support, y_support, x_query, y_query

    def get_history(self) -> List[TaskSpec]:
        return list(self.history)
