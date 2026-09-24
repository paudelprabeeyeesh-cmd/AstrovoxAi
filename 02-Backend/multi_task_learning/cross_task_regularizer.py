import math
from typing import Dict, List


class CrossTaskRegularizer:
    def __init__(self, strength: float = 0.1):
        self.strength = strength

    def compute_penalty(self, shared_reps: Dict[str, List[float]]) -> float:
        if len(shared_reps) < 2:
            return 0.0
        means = {}
        variances = {}
        for task, rep in shared_reps.items():
            n = len(rep)
            mean = sum(rep) / n
            variance = sum((x - mean) ** 2 for x in rep) / n
            means[task] = mean
            variances[task] = variance
        tasks = list(shared_reps.keys())
        pairs = len(tasks) * (len(tasks) - 1) / 2
        penalty = 0.0
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                penalty += (means[tasks[i]] - means[tasks[j]]) ** 2
                penalty += (variances[tasks[i]] - variances[tasks[j]]) ** 2
        return self.strength * penalty / pairs
