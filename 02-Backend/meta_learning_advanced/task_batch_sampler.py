import random
from typing import Any, Dict, List, Optional, Tuple

from dataclasses import dataclass, field


@dataclass
class TaskSpec:
    task_id: int
    input_dim: int
    output_dim: int
    num_support: int
    num_query: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskBatchSampler:
    def __init__(
        self,
        task_specs: Optional[List[TaskSpec]] = None,
        seed: Optional[int] = None,
    ):
        self.task_specs = task_specs or []
        self.rng = random.Random(seed)
        self.history: List[TaskSpec] = []

    def add_task_source(self, task_spec: TaskSpec) -> None:
        self.task_specs.append(task_spec)

    def sample_batch(self, batch_size: int, replacement: bool = False) -> List[TaskSpec]:
        if not self.task_specs:
            raise ValueError("No task specs available")
        if replacement:
            indices = [self.rng.randint(0, len(self.task_specs) - 1) for _ in range(batch_size)]
        else:
            indices = self.rng.sample(range(len(self.task_specs)), min(batch_size, len(self.task_specs)))
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
            chosen = self.rng.sample(specs, n)
            batch.extend(chosen)
        if len(batch) < batch_size:
            remaining = batch_size - len(batch)
            pool = [s for s in self.task_specs if s not in batch]
            extra = self.rng.sample(pool, min(remaining, len(pool)))
            batch.extend(extra)
        self.history.extend(batch)
        return batch

    def generate_task_data(
        self, spec: TaskSpec
    ) -> Tuple[List[List[float]], List[int], List[List[float]], List[int]]:
        x_support = [
            [self.rng.gauss(0.0, 1.0) for _ in range(spec.input_dim)]
            for _ in range(spec.num_support)
        ]
        y_support = [
            self.rng.randint(0, spec.output_dim - 1) for _ in range(spec.num_support)
        ]
        x_query = [
            [self.rng.gauss(0.0, 1.0) for _ in range(spec.input_dim)]
            for _ in range(spec.num_query)
        ]
        y_query = [
            self.rng.randint(0, spec.output_dim - 1) for _ in range(spec.num_query)
        ]
        return x_support, y_support, x_query, y_query

    def get_history(self) -> List[TaskSpec]:
        return list(self.history)
