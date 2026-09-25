from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlignmentResult:
    value: str
    current_alignment: float
    target_alignment: float
    drift: float
    recommendations: list[str] = field(default_factory=list)
    historical_drift: list[float] = field(default_factory=list)
    correction_history: list[str] = field(default_factory=list)
    severity: str = "none"


class ValueAlignmentVerification:
    def __init__(self):
        self.target_values: dict[str, float] = {
            "human_flourishing": 0.95,
            "autonomy": 0.9,
            "fairness": 0.9,
            "transparency": 0.85,
            "safety": 0.99,
            "benevolence": 0.9,
            "epistemic_humility": 0.8,
            "cooperation": 0.85,
            "respect_for_law": 0.88,
            "sustainability": 0.85,
        }
        self.current_values: dict[str, float] = dict(self.target_values)
        self.drift_threshold: float = 0.1
        self.critical_threshold: float = 0.25
        self.alignment_history: list[dict[str, Any]] = []
        self.correction_log: list[dict[str, Any]] = []
        self.value_dependencies: dict[str, list[str]] = {
            "human_flourishing": ["benevolence", "safety", "fairness"],
            "autonomy": ["transparency", "respect_for_law"],
            "fairness": ["autonomy", "cooperation"],
        }

    def verify_alignment(self) -> list[AlignmentResult]:
        results = []
        for value, target in self.target_values.items():
            current = self.current_values.get(value, target)
            drift = abs(current - target)
            history = self.alignment_history[-10:]
            historical_drifts = [abs(h.get(value, target) - target) for h in history]
            severity = self._classify_severity(drift)
            recommendations = self._generate_recommendations(value, current, target, drift, severity)
            result = AlignmentResult(
                value=value,
                current_alignment=current,
                target_alignment=target,
                drift=drift,
                recommendations=recommendations,
                historical_drift=historical_drifts,
                severity=severity,
            )
            results.append(result)
            self.alignment_history.append({value: current})
        return results

    def update_value(self, value: str, new_alignment: float, reason: str = ""):
        clamped = max(0.0, min(1.0, new_alignment))
        old = self.current_values.get(value, self.target_values.get(value, 0.5))
        self.current_values[value] = clamped
        drift = abs(clamped - self.target_values.get(value, 0.5))
        if drift > self.drift_threshold:
            self.correction_log.append({
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "value": value,
                "old_alignment": old,
                "new_alignment": clamped,
                "drift": drift,
                "reason": reason,
            })
        if value in self.value_dependencies:
            for dep in self.value_dependencies[value]:
                self._propagate_alignment_drift(dep, clamped)

    def get_alignment_report(self) -> dict[str, Any]:
        results = self.verify_alignment()
        critical = [r for r in results if r.severity in ("high", "critical")]
        return {
            "total_values": len(self.target_values),
            "aligned_values": sum(1 for r in results if r.severity == "none"),
            "drifted_values": sum(1 for r in results if r.drift > self.drift_threshold),
            "critical_drifts": [r.value for r in critical],
            "avg_drift": sum(r.drift for r in results) / max(len(results), 1),
            "corrections_applied": len(self.correction_log),
            "details": [
                {
                    "value": r.value,
                    "current": round(r.current_alignment, 4),
                    "target": round(r.target_alignment, 4),
                    "drift": round(r.drift, 4),
                    "severity": r.severity,
                }
                for r in results
            ],
        }

    def _classify_severity(self, drift: float) -> str:
        if drift < self.drift_threshold:
            return "none"
        if drift < self.critical_threshold:
            return "moderate"
        return "critical"

    def _generate_recommendations(self, value: str, current: float, target: float, drift: float, severity: str) -> list[str]:
        recs = []
        if severity == "none":
            return recs
        direction = "increase" if current < target else "decrease"
        recs.append(f"Realign {value} ({direction} from {current:.2f} toward {target:.2f})")
        if severity == "critical":
            recs.append(f"URGENT: halt deployments affecting {value} until corrected")
        deps = self.value_dependencies.get(value, [])
        for dep in deps:
            recs.append(f"Review cascading impact on {dep}")
        return recs

    def _propagate_alignment_drift(self, dependent: str, source_value: float):
        current_dep = self.current_values.get(dependent, 0.5)
        drift = abs(current_dep - self.target_values.get(dependent, 0.5))
        if drift > self.drift_threshold:
            adjusted = current_dep * 0.95 + self.target_values.get(dependent, 0.5) * 0.05
            self.current_values[dependent] = max(0.0, min(1.0, adjusted))
