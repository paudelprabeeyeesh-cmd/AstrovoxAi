from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class RiskCategory(str, Enum):
    MISALIGNMENT = "misalignment"
    LOSS_OF_CONTROL = "loss_of_control"
    SCALING_HAZARD = "scaling_hazard"
    EXISTENTIAL_CASCADE = "existential_cascade"
    VALUE_DRIFT = "value_drift"
    COGNITIVE_INFRASTRUCTURE = "cognitive_infrastructure"


class RiskSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CATASTROPHIC = "catastrophic"


@dataclass
class MitigationPlan:
    risk_id: str
    mitigations: List[str]
    residual_risk: float
    monitoring: List[str]


@dataclass
class RiskAssessment:
    category: RiskCategory
    severity: RiskSeverity
    probability: float
    impact: float
    mitigations: List[MitigationPlan]
    overall_risk_score: float = 0.0

    def __post_init__(self) -> None:
        if not self.overall_risk_score:
            self.overall_risk_score = self.probability * self.impact


class ExistentialRiskAssessor:
    def __init__(self) -> None:
        self.category_thresholds = {
            RiskCategory.MISALIGNMENT: 0.7,
            RiskCategory.LOSS_OF_CONTROL: 0.8,
            RiskCategory.SCALING_HAZARD: 0.6,
            RiskCategory.EXISTENTIAL_CASCADE: 0.9,
            RiskCategory.VALUE_DRIFT: 0.5,
            RiskCategory.COGNITIVE_INFRASTRUCTURE: 0.4,
        }

    def assess(self, category: RiskCategory, probability: float, impact: float) -> RiskAssessment:
        severity = RiskSeverity.LOW
        if probability > 0.9 or impact > 0.9:
            severity = RiskSeverity.CATASTROPHIC
        elif probability > 0.7 or impact > 0.7:
            severity = RiskSeverity.HIGH
        elif probability > 0.4 or impact > 0.4:
            severity = RiskSeverity.MODERATE
        mitigations = self._default_mitigations(category)
        return RiskAssessment(
            category=category,
            severity=severity,
            probability=probability,
            impact=impact,
            mitigations=mitigations,
        )

    def _default_mitigations(self, category: RiskCategory) -> List[MitigationPlan]:
        return [
            MitigationPlan(
                risk_id=f"{category.value}_1",
                mitigations=["implement_corrigibility", "enhance_interpretability", "add_shutdown_mechanism"],
                residual_risk=0.1,
                monitoring=["alignment_scores", "control_interfaces"],
            )
        ]
