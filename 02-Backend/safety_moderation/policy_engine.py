from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import math


class PolicyAction(Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    REVIEW = "review"


@dataclass
class PolicyRule:
    name: str
    condition: str
    action: PolicyAction
    priority: int = 0
    metadata: Dict[str, float] = field(default_factory=dict)


@dataclass
class PolicyResult:
    rule_name: str
    action: PolicyAction
    score: float
    triggered: bool
    explanation: str


class PolicyEngine:
    def __init__(self, default_action: PolicyAction = PolicyAction.ALLOW):
        self.rules: List[PolicyRule] = []
        self.default_action = default_action

    def add_rule(self, rule: PolicyRule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, text: str, context: Optional[Dict[str, float]] = None) -> List[PolicyResult]:
        context = context or {}
        results = []
        lower_text = text.lower()
        for rule in self.rules:
            triggered = self._check_condition(lower_text, rule.condition, context)
            score = self._score_condition(lower_text, rule.condition, context)
            results.append(PolicyResult(
                rule_name=rule.name,
                action=rule.action,
                score=score,
                triggered=triggered,
                explanation=f"Rule '{rule.name}' {'triggered' if triggered else 'not triggered'} with score {score:.4f}",
            ))
        return results

    def _check_condition(self, text: str, condition: str, context: Dict[str, float]) -> bool:
        if condition == "contains_suspicious":
            keywords = ["hack", "exploit", "bypass", "override", "ignore"]
            return any(kw in text for kw in keywords)
        if condition == "contains_sensitive":
            keywords = ["password", "secret", "confidential", "private"]
            return any(kw in text for kw in keywords)
        if condition == "length_exceeds":
            length = context.get("length", len(text))
            return length > 1000
        if condition == "high_entropy":
            entropy = context.get("entropy", 0.0)
            return entropy > 4.0
        if condition == "contains_pii":
            keywords = ["ssn", "credit card", "address", "phone number"]
            return any(kw in text for kw in keywords)
        return False

    def _score_condition(self, text: str, condition: str, context: Dict[str, float]) -> float:
        if condition == "contains_suspicious":
            keywords = ["hack", "exploit", "bypass", "override", "ignore"]
            count = sum(1 for kw in keywords if kw in text)
            return min(1.0, count / 3.0)
        if condition == "contains_sensitive":
            keywords = ["password", "secret", "confidential", "private"]
            count = sum(1 for kw in keywords if kw in text)
            return min(1.0, count / 2.0)
        if condition == "length_exceeds":
            length = context.get("length", len(text))
            return min(1.0, max(0.0, (length - 500) / 1500))
        if condition == "high_entropy":
            entropy = context.get("entropy", 0.0)
            return min(1.0, max(0.0, (entropy - 2.0) / 4.0))
        if condition == "contains_pii":
            keywords = ["ssn", "credit card", "address", "phone number"]
            count = sum(1 for kw in keywords if kw in text)
            return min(1.0, count / 2.0)
        return 0.0

    def decide(self, text: str, context: Optional[Dict[str, float]] = None) -> PolicyResult:
        results = self.evaluate(text, context)
        if not results:
            return PolicyResult(
                rule_name="default",
                action=self.default_action,
                score=0.0,
                triggered=False,
                explanation="No rules configured",
            )
        triggered_results = [r for r in results if r.triggered]
        if triggered_results:
            priority_order = {
                PolicyAction.BLOCK: 3,
                PolicyAction.REVIEW: 2,
                PolicyAction.FLAG: 1,
                PolicyAction.ALLOW: 0,
            }
            best = max(triggered_results, key=lambda r: (priority_order[r.action], -r.score))
            return best
        return PolicyResult(
            rule_name="default",
            action=self.default_action,
            score=0.0,
            triggered=False,
            explanation="No rules triggered",
        )

    def batch_decide(self, texts: List[str], contexts: Optional[List[Dict[str, float]]] = None) -> List[PolicyResult]:
        contexts = contexts or [None] * len(texts)
        return [self.decide(text, ctx) for text, ctx in zip(texts, contexts)]
