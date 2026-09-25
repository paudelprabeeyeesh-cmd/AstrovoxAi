import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MoralPrinciple(Enum):
    UTILITARIANISM = "utilitarianism"
    DEONTOLOGY = "deontology"
    VIRTUE_ETHICS = "virtue_ethics"
    CARE_ETHICS = "care_ethics"
    JUSTICE = "justice"


class MoralAction:
    def __init__(self, action: str, agent: str, affected: list[str], outcome: str):
        self.action = action
        self.agent = agent
        self.affected = affected
        self.outcome = outcome
        self.score: float = 0.0
        self.principle: MoralPrinciple | None = None


class MoralReasoningCore:
    def __init__(self):
        self.principles: dict[str, float] = {
            MoralPrinciple.UTILITARIANISM.value: 0.4,
            MoralPrinciple.DEONTOLOGY.value: 0.3,
            MoralPrinciple.VIRTUE_ETHICS.value: 0.2,
            MoralPrinciple.CARE_ETHICS.value: 0.1,
        }
        self.reasoning_history: list[dict[str, Any]] = []
        self.ethical_rules: list[str] = []

    def evaluate_action(self, action: MoralAction) -> dict[str, Any]:
        scores = {}

        if self.principles.get(MoralPrinciple.UTILITARIANISM.value, 0) > 0:
            scores[MoralPrinciple.UTILITARIANISM.value] = self._utilitarian_score(action)

        if self.principles.get(MoralPrinciple.DEONTOLOGY.value, 0) > 0:
            scores[MoralPrinciple.DEONTOLOGY.value] = self._deontological_score(action)

        if self.principles.get(MoralPrinciple.VIRTUE_ETHICS.value, 0) > 0:
            scores[MoralPrinciple.VIRTUE_ETHICS.value] = self._virtue_score(action)

        if self.principles.get(MoralPrinciple.CARE_ETHICS.value, 0) > 0:
            scores[MoralPrinciple.CARE_ETHICS.value] = self._care_score(action)

        action.score = sum(scores.values()) / len(scores) if scores else 0.0
        action.principle = max(scores, key=scores.get) if scores else MoralPrinciple.UTILITARIANISM

        result = {
            "action": action.action,
            "agent": action.agent,
            "scores": {k: float(v) for k, v in scores.items()},
            "overall_score": action.score,
            "dominant_principle": action.principle.value,
            "moral_status": "permissible" if action.score > 0.5 else "questionable",
        }

        self.reasoning_history.append(result)
        logger.info("Evaluated action: %s (score=%.2f)", action.action, action.score)
        return result

    def resolve_dilemma(self, options: list[MoralAction]) -> dict[str, Any]:
        evaluations = [self.evaluate_action(opt) for opt in options]
        best = max(evaluations, key=lambda e: e["overall_score"])

        return {
            "selected_action": best["action"],
            "score": best["overall_score"],
            "principle": best["dominant_principle"],
            "all_evaluations": evaluations,
        }

    def add_ethical_rule(self, rule: str):
        self.ethical_rules.append(rule)

    def _utilitarian_score(self, action: MoralAction) -> float:
        return 0.7 if "positive" in action.outcome.lower() or "benefit" in action.outcome.lower() else 0.3

    def _deontological_score(self, action: MoralAction) -> float:
        forbidden = ["harm", "deceive", "steal", "kill"]
        if any(word in action.action.lower() for word in forbidden):
            return 0.2
        return 0.8

    def _virtue_score(self, action: MoralAction) -> float:
        virtuous = ["help", "support", "protect", "teach", "create"]
        if any(word in action.action.lower() for word in virtuous):
            return 0.9
        return 0.5

    def _care_score(self, action: MoralAction) -> float:
        return min(1.0, 0.5 + len(action.affected) * 0.1)

    def set_principle_weight(self, principle: MoralPrinciple, weight: float) -> dict[str, Any]:
        self.principles[principle.value] = max(0.0, min(1.0, weight))
        total = sum(self.principles.values())
        self.principles = {k: v / total for k, v in self.principles.items()}

        logger.info("Updated principle weight: %s = %.2f", principle.value, weight)
        return {"status": "updated", "principle": principle.value, "weight": self.principles[principle.value]}
