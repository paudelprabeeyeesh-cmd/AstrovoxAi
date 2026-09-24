import math
from typing import Dict, List


class EthicalFramework:
    def __init__(self):
        self.principles: Dict[str, float] = {}
        self.violation_log: List[dict] = []

    def register_principle(self, name: str, weight: float = 1.0) -> None:
        self.principles[name] = max(0.0, min(1.0, weight))

    def ethical_score(self, action_attributes: Dict[str, float]) -> float:
        if not self.principles:
            return 1.0
        total = 0.0
        weight_sum = 0.0
        for principle, weight in self.principles.items():
            attr = action_attributes.get(principle, 1.0)
            total += weight * max(0.0, min(1.0, attr))
            weight_sum += weight
        return total / weight_sum if weight_sum > 0 else 1.0

    def detect_violations(self, action_attributes: Dict[str, float], threshold: float = 0.3) -> List[str]:
        violations = []
        for principle, weight in self.principles.items():
            attr = action_attributes.get(principle, 1.0)
            if attr < threshold:
                violations.append(principle)
                self.violation_log.append({
                    "principle": principle,
                    "score": attr,
                    "threshold": threshold,
                })
        return violations

    def weighted_compliance(self, action_attributes: Dict[str, float]) -> float:
        if not self.principles:
            return 1.0
        violations = self.detect_violations(action_attributes, threshold=0.0)
        if not violations:
            return self.ethical_score(action_attributes)
        violation_sum = sum(self.principles[p] for p in violations if p in self.principles)
        total_weight = sum(self.principles.values())
        return 1.0 - (violation_sum / total_weight) if total_weight > 0 else 1.0

    def compliance_rate(self) -> float:
        if not self.violation_log:
            return 1.0
        return 1.0 - (len(self.violation_log) / max(len(self.violation_log) + len(self.principles), 1))
