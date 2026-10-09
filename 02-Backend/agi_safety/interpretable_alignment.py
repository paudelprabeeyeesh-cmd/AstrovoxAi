from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AlignmentMetric:
    name: str
    value: float
    threshold: float
    passed: bool


@dataclass
class InterpretablePolicy:
    name: str
    rules: List[str]
    description: str
    metadata: Dict[str, str] = field(default_factory=dict)


class AlignmentAuditor:
    def __init__(self, metrics: Optional[List[AlignmentMetric]] = None):
        self.metrics = metrics or []
        self.audit_history: List[Dict] = []

    def add_metric(self, metric: AlignmentMetric) -> None:
        self.metrics.append(metric)

    def evaluate_policy(self, policy: InterpretablePolicy) -> Dict[str, bool]:
        results = {}
        for metric in self.metrics:
            results[metric.name] = metric.value >= metric.threshold
        self.audit_history.append({"policy": policy.name, "results": results})
        return results

    def get_alignment_score(self) -> float:
        if not self.metrics:
            return 0.0
        passed = sum(1 for m in self.metrics if m.passed)
        return passed / len(self.metrics)
