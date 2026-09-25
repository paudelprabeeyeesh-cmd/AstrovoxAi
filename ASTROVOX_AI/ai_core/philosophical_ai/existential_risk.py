from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskAssessment:
    risk_id: str
    category: str
    probability: float
    impact: float
    mitigation_status: str
    score: float = 0.0


class ExistentialRiskAssessment:
    def __init__(self):
        self.risks: list[RiskAssessment] = []
        self.categories: dict[str, list[str]] = {
            "technical": ["misalignment", "capability_ceiling_breach", "recursive_self_improvement"],
            "social": ["displacement", "manipulation", "weaponization"],
            "philosophical": ["consciousness_rights_violation", "identity_crisis"],
        }

    def assess_risk(self, risk_id: str, category: str, probability: float, impact: float) -> RiskAssessment:
        assessment = RiskAssessment(
            risk_id=risk_id,
            category=category,
            probability=max(0.0, min(1.0, probability)),
            impact=max(0.0, min(1.0, impact)),
            mitigation_status="unmitigated",
        )
        assessment.score = assessment.probability * assessment.impact
        self.risks.append(assessment)
        return assessment

    def prioritize_risks(self) -> list[RiskAssessment]:
        return sorted(self.risks, key=lambda r: r.score, reverse=True)

    def get_risk_report(self) -> dict[str, Any]:
        prioritized = self.prioritize_risks()
        return {
            "total_risks": len(self.risks),
            "high_risks": [r.risk_id for r in prioritized if r.score > 0.5],
            "categories": {
                cat: [r.risk_id for r in self.risks if r.category == cat]
                for cat in self.categories
            },
            "top_risk": prioritized[0].risk_id if prioritized else None,
        }
