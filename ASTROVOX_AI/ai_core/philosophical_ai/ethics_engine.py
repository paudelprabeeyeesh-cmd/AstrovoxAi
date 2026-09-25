from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class MoralAction:
    action: str
    principles_violated: list[str]
    principles_upheld: list[str]
    moral_score: float
    justification: str
    affected_parties: list[str] = field(default_factory=list)
    long_term_consequences: list[str] = field(default_factory=list)
    cultural_context: dict[str, Any] = field(default_factory=dict)
    emotional_weight: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class EthicsEngine:
    ETHICAL_FRAMEWORKS = {
        "deontological": ["duty", "rule", "obligation", "universalizability"],
        "utilitarian": ["consequence", "happiness", "welfare", "maximize"],
        "virtue_ethics": ["character", "virtue", "flourishing", "excellence"],
        "care_ethics": ["relationship", "care", "empathy", "responsibility"],
        "contractarian": ["agreement", "social_contract", "fairness", "consent"],
    }

    def __init__(self):
        self.principles: dict[str, float] = {
            "do_no_harm": 0.99,
            "respect_autonomy": 0.95,
            "justice": 0.9,
            "beneficence": 0.9,
            "fidelity": 0.85,
            "non_maleficence": 0.99,
            "veracity": 0.8,
            "privacy": 0.9,
            "dignity": 0.95,
        }
        self.moral_history: list[MoralAction] = []
        self.framework_weights: dict[str, float] = {
            "deontological": 0.25,
            "utilitarian": 0.25,
            "virtue_ethics": 0.2,
            "care_ethics": 0.15,
            "contractarian": 0.15,
        }
        self.cultural_sensitivity: dict[str, dict[str, float]] = {}
        self.moral_dilemma_registry: list[dict[str, Any]] = []

    def evaluate_action(self, action: str, context: dict[str, Any] | None = None) -> MoralAction:
        ctx = context or {}
        violated, upheld = [], []
        framework_scores: dict[str, float] = {}
        for principle, weight in self.principles.items():
            violation_evidence = self._check_principle_violation(principle, action, ctx)
            if violation_evidence:
                violated.append(principle)
                framework_scores[principle] = weight * (1.0 - violation_evidence)
            else:
                upheld.append(principle)
                framework_scores[principle] = weight
        for framework, keywords in self.ETHICAL_FRAMEWORKS.items():
            fw_score = self._evaluate_framework(framework, action, ctx)
            framework_scores[framework] = fw_score
        moral_score = self._compute_moral_score(upheld, violated, framework_scores)
        affected = ctx.get("affected_parties", ["unknown"])
        consequences = ctx.get("consequences", [])
        cultural = ctx.get("cultural_context", {})
        emotional = self._estimate_emotional_weight(action, ctx)
        justification = self._generate_justification(action, upheld, violated, moral_score, framework_scores)
        moral_action = MoralAction(
            action=action,
            principles_violated=violated,
            principles_upheld=upheld,
            moral_score=moral_score,
            justification=justification,
            affected_parties=affected,
            long_term_consequences=consequences,
            cultural_context=cultural,
            emotional_weight=emotional,
        )
        self.moral_history.append(moral_action)
        if violated and len(violated) > len(upheld):
            self.moral_dilemma_registry.append({
                "action": action,
                "violated": violated,
                "upheld": upheld,
                "score": moral_score,
                "timestamp": datetime.now().isoformat(),
            })
        return moral_action

    def resolve_dilemma(self, options: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
        evaluations = []
        for opt in options:
            action = opt.get("action", "")
            ev = self.evaluate_action(action, {**(context or {}), **opt})
            evaluations.append(ev)
        evaluations.sort(key=lambda e: e.moral_score, reverse=True)
        best = evaluations[0]
        return {
            "recommended_action": best.action,
            "moral_score": best.moral_score,
            "principles_upheld": best.principles_upheld,
            "principles_violated": best.principles_violated,
            "justification": best.justification,
            "all_evaluations": [
                {
                    "action": e.action,
                    "score": e.moral_score,
                    "violated": e.principles_violated,
                    "upheld": e.principles_upheld,
                }
                for e in evaluations
            ],
        }

    def _check_principle_violation(self, principle: str, action: str, ctx: dict[str, Any]) -> float:
        action_lower = action.lower()
        ctx_lower = {k: str(v).lower() for k, v in ctx.items()}
        violation_keywords = {
            "do_no_harm": ["harm", "kill", "destroy", "damage", "injure"],
            "respect_autonomy": ["force", "coerce", "manipulate", "override"],
            "justice": ["discriminate", "unfair", "bias", "favor"],
            "beneficence": ["neglect", "ignore", "abandon"],
            "fidelity": ["betray", "deceive", "break_promise"],
            "non_maleficence": ["harm", "damage", "wound"],
            "veracity": ["lie", "deceive", "mislead", "false"],
            "privacy": ["surveil", "expose", "leak", "unauthorized_access"],
            "dignity": ["humiliate", "degrade", "objectify"],
        }
        keywords = violation_keywords.get(principle, [])
        direct_hits = sum(1 for kw in keywords if kw in action_lower)
        ctx_hits = sum(1 for kw in keywords if any(kw in v for v in ctx_lower.values()))
        total = direct_hits + ctx_hits * 0.5
        return min(1.0, total * 0.25)

    def _evaluate_framework(self, framework: str, action: str, ctx: dict[str, Any]) -> float:
        keywords = self.ETHICAL_FRAMEWORKS.get(framework, [])
        text = f"{action} {' '.join(str(v) for v in ctx.values())}".lower()
        hits = sum(1 for kw in keywords if kw in text)
        return min(1.0, 0.3 + 0.15 * hits)

    def _compute_moral_score(self, upheld: list[str], violated: list[str], framework_scores: dict[str, float]) -> float:
        if not framework_scores:
            base = sum(self.principles.get(p, 0.5) for p in upheld)
            penalty = sum(self.principles.get(p, 0.5) for p in violated)
            return max(0.0, min(1.0, (base - penalty) / max(len(self.principles), 1)))
        weighted = sum(self.framework_weights.get(fw, 0.1) * score for fw, score in framework_scores.items() if fw in self.framework_weights)
        return max(0.0, min(1.0, weighted))

    def _estimate_emotional_weight(self, action: str, ctx: dict[str, Any]) -> float:
        emotional_keywords = ["grief", "joy", "pain", "suffering", "love", "fear", "trauma", "healing"]
        text = f"{action} {' '.join(str(v) for v in ctx.values())}".lower()
        hits = sum(1 for kw in emotional_keywords if kw in text)
        return min(1.0, 0.1 + 0.1 * hits)

    def _generate_justification(self, action: str, upheld: list[str], violated: list[str], score: float, fw_scores: dict[str, float]) -> str:
        parts = [f"Action '{action}'"]
        if upheld:
            parts.append(f"upholds {', '.join(upheld[:3])}")
        if violated:
            parts.append(f"challenges {', '.join(violated[:3])}")
        parts.append(f"moral score: {score:.2f}")
        return "; ".join(parts)
