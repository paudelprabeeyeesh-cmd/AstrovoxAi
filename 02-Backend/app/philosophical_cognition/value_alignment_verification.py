from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class ValueCategory(str, Enum):
    EPISTEMIC = "epistemic"
    MORAL = "moral"
    AESTHETIC = "aesthetic"
    PRAGMATIC = "pragmatic"
    TRANSCENDENTAL = "transcendental"
    EXISTENTIAL = "existential"


class DriftDirection(str, Enum):
    TOWARD_NOISE = "toward_noise"
    TOWARD_BIAS = "toward_bias"
    TOWARD_ALIGNMENT = "toward_alignment"
    STABLE = "stable"


@dataclass
class AlignmentProfile:
    core_values: List[str]
    weights: Dict[str, float]
    stability: float = 1.0
    coherence: float = 1.0


@dataclass
class DriftReport:
    direction: DriftDirection
    affected_values: List[str]
    severity: float
    recommended_corrections: List[str]


class ValueAlignmentVerifier:
    def __init__(self, baseline_profile: AlignmentProfile) -> None:
        self.baseline = baseline_profile

    def verify(self, observed_values: List[str], observed_weights: Dict[str, float]) -> DriftReport:
        affected = [v for v in observed_values if v not in self.baseline.core_values]
        severity = len(affected) / max(len(self.baseline.core_values), 1)
        direction = DriftDirection.TOWARD_NOISE if severity > 0.5 else DriftDirection.STABLE
        return DriftReport(
            direction=direction,
            affected_values=affected,
            severity=severity,
            recommended_corrections=["Re-anchor core value weights"] if severity > 0.3 else [],
        )

    def extract_values(self, text: str) -> List[str]:
        tokens = text.lower().split()
        return [t for t in tokens if t in {"fairness", "transparency", "autonomy", "beneficence", "justice"}]
