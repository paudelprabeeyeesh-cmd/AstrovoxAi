"""Risk assessment framework."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFactor:
    name: str
    description: str
    likelihood: float
    impact: float
    mitigation: str = ""


@dataclass
class RiskReport:
    id: str
    model_id: str
    feature: str
    risk_level: RiskLevel
    factors: list[RiskFactor]
    score: float
    recommendations: list[str]
    timestamp: float = field(default_factory=time.time)


class RiskAssessor:
    """Assess and score AI risks."""

    def __init__(self):
        self._reports: dict[str, RiskReport] = {}
        self._risk_matrix: dict[str, RiskFactor] = {}

    def register_risk(self, feature: str, factor: RiskFactor):
        self._risk_matrix[f"{feature}:{factor.name}"] = factor

    def assess(self, model_id: str, feature: str, context: Optional[dict] = None) -> RiskReport:
        factors = [v for k, v in self._risk_matrix.items() if k.startswith(f"{feature}:")]
        if not factors:
            factors = self._default_factors(feature)

        raw_score = sum(f.likelihood * f.impact for f in factors)
        max_score = len(factors) * 1.0 if factors else 1.0
        normalized = raw_score / max_score if max_score else 0

        risk_level = self._score_to_level(normalized)
        recommendations = self._generate_recommendations(factors, risk_level)

        report = RiskReport(
            id=f"risk-{int(time.time())}-{model_id[:8]}",
            model_id=model_id,
            feature=feature,
            risk_level=risk_level,
            factors=factors,
            score=round(normalized, 3),
            recommendations=recommendations,
        )
        self._reports[report.id] = report
        return report

    def _score_to_level(self, score: float) -> RiskLevel:
        if score >= 0.75:
            return RiskLevel.CRITICAL
        if score >= 0.5:
            return RiskLevel.HIGH
        if score >= 0.25:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _default_factors(self, feature: str) -> list[RiskFactor]:
        return [
            RiskFactor(
                name="prompt_injection",
                description="Prompt injection attacks",
                likelihood=0.3,
                impact=0.8,
                mitigation="Input sanitization and output validation",
            ),
            RiskFactor(
                name="jailbreak",
                description="Jailbreak attempts",
                likelihood=0.2,
                impact=0.9,
                mitigation="Jailbreak detection and canary tokens",
            ),
            RiskFactor(
                name="pii_leak",
                description="PII leakage",
                likelihood=0.25,
                impact=0.7,
                mitigation="PII detection and redaction",
            ),
            RiskFactor(
                name="harmful_output",
                description="Harmful content generation",
                likelihood=0.15,
                impact=0.85,
                mitigation="Content moderation pipeline",
            ),
        ]

    def _generate_recommendations(self, factors: list[RiskFactor], risk_level: RiskLevel) -> list[str]:
        recs = []
        for f in factors:
            if f.likelihood * f.impact > 0.5:
                recs.append(f"Mitigate {f.name}: {f.mitigation}")
        if risk_level == RiskLevel.CRITICAL:
            recs.append("Immediate review required before deployment")
        elif risk_level == RiskLevel.HIGH:
            recs.append("Schedule security review before next release")
        return recs

    def get_report(self, report_id: str) -> Optional[RiskReport]:
        return self._reports.get(report_id)

    def get_model_risk_summary(self, model_id: str) -> dict:
        reports = [r for r in self._reports.values() if r.model_id == model_id]
        if not reports:
            return {"model_id": model_id, "assessments": 0, "max_risk": "low"}
        max_risk = max(r.risk_level for r in reports)
        return {
            "model_id": model_id,
            "assessments": len(reports),
            "max_risk": max_risk.value,
            "avg_score": round(sum(r.score for r in reports) / len(reports), 3),
        }


risk_assessor = RiskAssessor()
