import numpy as np
from typing import List, Dict, Optional


class Insect:
    def __init__(self, insect_id: int, tasks: List[str], thresholds: List[float], seed: Optional[int] = None):
        self.insect_id = insect_id
        self.tasks = tasks
        self.thresholds = dict(zip(tasks, thresholds))
        self.current_task: Optional[str] = None
        self.rng = np.random.default_rng(seed)
        self.task_load: Dict[str, int] = {t: 0 for t in tasks}
        self.response: Dict[str, float] = {t: 0.0 for t in tasks}

    def respond(self, stimuli: Dict[str, float], noise: float = 0.1) -> None:
        for task in self.tasks:
            s = stimuli.get(task, 0.0)
            self.response[task] = max(0.0, s - self.thresholds[task] + self.rng.normal(0, noise))

    def assign_task(self) -> Optional[str]:
        if not self.response:
            return None
        best_task = max(self.response, key=lambda t: self.response[t])
        if self.response[best_task] > 0:
            self.current_task = best_task
            self.task_load[best_task] += 1
            return best_task
        self.current_task = None
        return None


class InsectColony:
    def __init__(self, n_insects: int, tasks: List[str], seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.tasks = tasks
        thresholds = [self.rng.uniform(0.2, 0.8) for _ in tasks]
        self.insects = [Insect(i, tasks, thresholds, seed=seed) for i in range(n_insects)]
        self.stimuli: Dict[str, float] = {t: 0.0 for t in tasks}
        self.task_allocation: Dict[str, List[int]] = {t: [] for t in tasks}
        self.efficiency_history: List[float] = []

    def update_stimuli(self, demands: Dict[str, float]) -> None:
        for task in self.tasks:
            self.stimuli[task] = demands.get(task, 0.0) + self.task_allocation[task].__len__() * 0.1

    def allocate(self, noise: float = 0.1) -> Dict[str, int]:
        self.task_allocation = {t: [] for t in self.tasks}
        for insect in self.insects:
            insect.respond(self.stimuli, noise=noise)
            task = insect.assign_task()
            if task is not None:
                self.task_allocation[task].append(insect.insect_id)
        return {t: len(self.task_allocation[t]) for t in self.tasks}

    def efficiency(self, demands: Dict[str, float]) -> float:
        total_error = 0.0
        for task in self.tasks:
            supplied = len(self.task_allocation.get(task, []))
            demand = demands.get(task, 0.0)
            total_error += abs(supplied - demand)
        eff = 1.0 / (1.0 + total_error)
        self.efficiency_history.append(eff)
        return eff

    def optimize(self, demands: Dict[str, float], iterations: int = 20, noise: float = 0.1) -> List[float]:
        for _ in range(iterations):
            self.update_stimuli(demands)
            self.allocate(noise=noise)
            self.efficiency(demands)
        return self.efficiency_history
