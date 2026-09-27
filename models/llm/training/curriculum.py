import math
import random
import logging
from typing import Dict, List, Optional, Tuple

import torch
from torch.utils.data import Subset

logger = logging.getLogger(__name__)


class CurriculumSampler:
    def __init__(self, datasets: Dict[str, torch.utils.data.Dataset], schedule: List[Tuple[str, float]]):
        self.datasets = datasets
        self.schedule = schedule
        self._current_domain = schedule[0][0] if schedule else list(datasets.keys())[0]
        self._current_weight = 1.0

    def set_step(self, step: int, total_steps: int):
        progress = step / max(total_steps, 1)
        weights = []
        domains = []
        for domain, weight in self.schedule:
            domains.append(domain)
            weights.append(weight)
        if not weights:
            return
        idx = min(int(progress * len(weights)), len(weights) - 1)
        self._current_domain = domains[idx]
        self._current_weight = weights[idx]

    def sample(self, batch_size: int) -> List[int]:
        ds = self.datasets.get(self._current_domain)
        if ds is None:
            return []
        n = len(ds)
        if n == 0:
            return []
        return [random.randint(0, n - 1) for _ in range(batch_size)]


class CurriculumScheduler:
    def __init__(self, phases: List[Dict]):
        self.phases = phases
        self.current_phase = 0

    def get_domain_weights(self, step: int) -> Dict[str, float]:
        phase_idx = 0
        for i, phase in enumerate(self.phases):
            if step >= phase.get("start_step", 0):
                phase_idx = i
        phase = self.phases[phase_idx]
        return phase.get("domain_weights", {})

    def get_lr_multiplier(self, step: int) -> float:
        phase = self.phases[-1]
        warmup = phase.get("warmup_steps", 0)
        if step < warmup:
            return step / max(warmup, 1)
        return 1.0
