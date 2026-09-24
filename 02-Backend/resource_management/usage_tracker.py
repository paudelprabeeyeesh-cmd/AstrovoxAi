from collections import defaultdict
from typing import Dict, Tuple


class UsageTracker:
    def __init__(self) -> None:
        self._usage: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def record(self, subject: str, resource: str, amount: float = 1.0) -> None:
        self._usage[subject][resource] += amount

    def get(self, subject: str, resource: str) -> float:
        return self._usage[subject][resource]

    def reset(self, subject: str, resource: str) -> None:
        self._usage[subject][resource] = 0.0

    def report(self) -> Dict[str, Dict[str, float]]:
        return {k: dict(v) for k, v in self._usage.items()}
