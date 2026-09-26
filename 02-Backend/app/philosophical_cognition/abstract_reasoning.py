from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ReasoningMode(str, Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    COUNTERFACTUAL = "counterfactual"


class InsightType(str, Enum):
    STRUCTURAL = "structural"
    FUNCTIONAL = "functional"
    CAUSAL = "causal"
    TELEOLOGICAL = "teleological"
    EMERGENT = "emergent"


@dataclass
class ReasoningContext:
    premises: List[str]
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    mode: ReasoningMode = ReasoningMode.DEDUCTIVE
    depth: int = 3
    evidence: List[str] = field(default_factory=list)


@dataclass
class Insight:
    statement: str
    insight_type: InsightType
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    abstraction_level: int = 1


class AbstractReasoningEngine:
    def __init__(self) -> None:
        self.mode_weights = {
            ReasoningMode.DEDUCTIVE: 1.0,
            ReasoningMode.INDUCTIVE: 0.9,
            ReasoningMode.ABDUCTIVE: 0.85,
            ReasoningMode.ANALOGICAL: 0.8,
            ReasoningMode.CAUSAL: 0.95,
            ReasoningMode.COUNTERFACTUAL: 0.75,
        }

    def reason(self, context: ReasoningContext) -> List[Insight]:
        insights: List[Insight] = []
        if context.mode == ReasoningMode.ANALOGICAL:
            insights.extend(self._analogical(context))
        elif context.mode == ReasoningMode.CAUSAL:
            insights.extend(self._causal(context))
        elif context.mode == ReasoningMode.COUNTERFACTUAL:
            insights.extend(self._counterfactual(context))
        elif context.mode == ReasoningMode.ABDUCTIVE:
            insights.extend(self._abductive(context))
        elif context.mode == ReasoningMode.INDUCTIVE:
            insights.extend(self._inductive(context))
        else:
            insights.extend(self._deductive(context))
        return insights

    def _deductive(self, context: ReasoningContext) -> List[Insight]:
        return [
            Insight(
                statement=f"Given premises, deduce: {context.premises[-1] if context.premises else 'N/A'}",
                insight_type=InsightType.STRUCTURAL,
                confidence=0.9,
            )
        ]

    def _inductive(self, context: ReasoningContext) -> List[Insight]:
        return [
            Insight(
                statement=f"Pattern from evidence suggests generalization over {len(context.evidence)} items",
                insight_type=InsightType.FUNCTIONAL,
                confidence=0.8,
            )
        ]

    def _abductive(self, context: ReasoningContext) -> List[Insight]:
        return [
            Insight(
                statement="Best explanation inferred from observations",
                insight_type=InsightType.CAUSAL,
                confidence=0.7,
            )
        ]

    def _analogical(self, context: ReasoningContext) -> List[Insight]:
        return [
            Insight(
                statement="Structural mapping across domains implies transferable relations",
                insight_type=InsightType.STRUCTURAL,
                confidence=0.75,
                abstraction_level=2,
            )
        ]

    def _causal(self, context: ReasoningContext) -> List[Insight]:
        return [
            Insight(
                statement="Causal chain reconstructed from temporal precedence and mechanism",
                insight_type=InsightType.CAUSAL,
                confidence=0.85,
            )
        ]

    def _counterfactual(self, context: ReasoningContext) -> List[Insight]:
        return [
            Insight(
                statement="Counterfactual scenario exposes necessary/sufficient conditions",
                insight_type=InsightType.EMERGENT,
                confidence=0.65,
            )
        ]

    def detect_contradictions(self, insights: List[Insight]) -> List[str]:
        contradictions: List[str] = []
        for insight in insights:
            for other in insights:
                if insight is not other and insight.statement == other.statement:
                    continue
                if set(insight.supporting_evidence) & set(other.contradictions):
                    contradictions.append(f"{insight.statement} conflicts with {other.statement}")
        return contradictions
