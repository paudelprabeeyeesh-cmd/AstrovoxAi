"""Risk scoring and threat modeling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass
class Threat:
    id: str
    name: str
    category: str
    likelihood: float
    impact: float
    description: str


@dataclass
class RiskControl:
    name: str
    effectiveness: float


@dataclass
class RiskScore:
    threat_id: str
    raw_score: float
    residual_score: float
    risk_level: str
    controls_applied: list[str]


_STRIDE_CATEGORIES = ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]


class RiskEngine:
    def __init__(self, controls: Sequence[RiskControl] | None = None) -> None:
        self.controls = list(controls or [])
        self._threats: dict[str, Threat] = {}

    def register_threat(self, threat: Threat) -> None:
        self._threats[threat.id] = threat

    def likelihood_score(self, threat: Threat) -> float:
        return max(0.0, min(1.0, threat.likelihood))

    def impact_score(self, threat: Threat) -> float:
        return max(0.0, min(1.0, threat.impact))

    def raw_risk(self, threat: Threat) -> float:
        return self.likelihood_score(threat) * self.impact_score(threat)

    def residual_risk(self, threat: Threat) -> float:
        raw = self.raw_risk(threat)
        if not self.controls:
            return raw
        reduction = 1.0 - np.prod([1.0 - c.effectiveness for c in self.controls])
        return max(0.0, raw * (1.0 - reduction))

    def score_threat(self, threat: Threat) -> RiskScore:
        raw = self.raw_risk(threat)
        residual = self.residual_risk(threat)
        if residual >= 0.7:
            level = "critical"
        elif residual >= 0.5:
            level = "high"
        elif residual >= 0.3:
            level = "medium"
        else:
            level = "low"
        return RiskScore(threat_id=threat.id, raw_score=raw, residual_score=residual, risk_level=level, controls_applied=[c.name for c in self.controls])

    def risk_matrix(self) -> dict[str, np.ndarray]:
        matrix = np.zeros((5, 5), dtype=np.float64)
        for t in self._threats.values():
            li = min(int(np.floor(self.likelihood_score(t) * 5)), 4)
            ii = min(int(np.floor(self.impact_score(t) * 5)), 4)
            matrix[li, ii] += 1.0
        return {"matrix": matrix, "likelihood_bins": 5, "impact_bins": 5}

    def aggregate_risk(self) -> dict:
        if not self._threats:
            return {"count": 0, "mean_raw": 0.0, "mean_residual": 0.0, "critical_count": 0}
        scores = [self.score_threat(t) for t in self._threats.values()]
        raw_arr = np.array([s.raw_score for s in scores], dtype=np.float64)
        res_arr = np.array([s.residual_score for s in scores], dtype=np.float64)
        return {
            "count": len(scores),
            "mean_raw": float(np.mean(raw_arr)),
            "mean_residual": float(np.mean(res_arr)),
            "std_residual": float(np.std(res_arr)),
            "critical_count": int(np.sum(res_arr >= 0.7)),
            "high_count": int(np.sum((res_arr >= 0.5) & (res_arr < 0.7))),
        }
