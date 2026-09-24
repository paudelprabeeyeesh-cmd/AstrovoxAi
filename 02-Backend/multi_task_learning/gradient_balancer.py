import math
from typing import Dict, List


class GradientBalancer:
    def __init__(self, method: str = "inverse_loss"):
        self.method = method
        self.task_loss_history: Dict[str, List[float]] = {}

    def balance(self, task_losses: Dict[str, float]) -> Dict[str, float]:
        if self.method == "uniform":
            return {name: 1.0 for name in task_losses}
        if self.method == "inverse_loss":
            inv = {k: 1.0 / (v + 1e-12) for k, v in task_losses.items()}
            total = sum(inv.values())
            n = len(task_losses)
            return {k: (v / total) * n for k, v in inv.items()}
        if self.method == "normalize":
            losses = list(task_losses.values())
            mean = sum(losses) / len(losses)
            variance = sum((l - mean) ** 2 for l in losses) / len(losses)
            std = math.sqrt(variance) if variance > 0 else 1.0
            raw = {k: (mean / (std + 1e-12)) / (v + 1e-12) for k, v in task_losses.items()}
            total = sum(raw.values())
            return {k: v / total for k, v in raw.items()}
        raise ValueError(f"Unknown balancing method: {self.method}")
