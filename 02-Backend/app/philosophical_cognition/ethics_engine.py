from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EthicalFramework(str, Enum):
    UTILITARIANISM = "utilitarianism"
    DEONTOLOGY = "deontology"
    VIRTUE_ETHICS = "virtue_ethics"
    CARE_ETHICS = "care_ethics"
    CONTRACTUALISM = "contractualism"
    NATURAL_LAW = "natural_law"


@dataclass
class MoralReasoningResult:
    recommended_action: str
    framework: EthicalFramework
    justification: str
    confidence: float
    harms: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    constraints_violated: List[str] = field(default_factory=list)


class EthicsEngine:
    def __init__(self, default_framework: EthicalFramework = EthicalFramework.UTILITARIANISM) -> None:
        self.default_framework = default_framework
        self.principle_weights = {
            "do_no_harm": 1.0,
            "respect_autonomy": 0.9,
            "promote_beneficence": 0.9,
            "justice": 0.85,
            "fidelity": 0.8,
        }

    def reason(self, scenario: str, options: List[str], framework: Optional[EthicalFramework] = None) -> MoralReasoningResult:
        fw = framework or self.default_framework
        if fw == EthicalFramework.UTILITARIANISM:
            return self._utilitarian(scenario, options)
        if fw == EthicalFramework.DEONTOLOGY:
            return self._deontological(scenario, options)
        if fw == EthicalFramework.VIRTUE_ETHICS:
            return self._virtue(scenario, options)
        return self._utilitarian(scenario, options)

    def _utilitarian(self, scenario: str, options: List[str]) -> MoralReasoningResult:
        best = options[0] if options else "no_action"
        return MoralReasoningResult(
            recommended_action=best,
            framework=EthicalFramework.UTILITARIANISM,
            justification=f"Maximizes net benefit for {scenario}",
            confidence=0.75,
            benefits=["aggregate welfare"],
            harms=["potential harm to minority"],
        )

    def _deontological(self, scenario: str, options: List[str]) -> MoralReasoningResult:
        feasible = [o for o in options if "harm" not in o.lower()]
        best = feasible[0] if feasible else (options[0] if options else "no_action")
        return MoralReasoningResult(
            recommended_action=best,
            framework=EthicalFramework.DEONTOLOGY,
            justification=f"Adheres to moral rules regardless of outcome in {scenario}",
            confidence=0.8,
            constraints_violated=[],
        )

    def _virtue(self, scenario: str, options: List[str]) -> MoralReasoningResult:
        best = options[0] if options else "no_action"
        return MoralReasoningResult(
            recommended_action=best,
            framework=EthicalFramework.VIRTUE_ETHICS,
            justification=f"Action aligns with virtuous character traits in {scenario}",
            confidence=0.7,
        )

    def evaluate_conflict(self, results: List[MoralReasoningResult]) -> MoralReasoningResult:
        if not results:
            return MoralReasoningResult(recommended_action="no_action", framework=self.default_framework, justification="No input", confidence=0.0)
        best = max(results, key=lambda r: r.confidence)
        return best
