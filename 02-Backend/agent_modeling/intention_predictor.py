import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Action:
    action_type: str
    target: str
    timestamp: float
    context: Dict[str, str] = field(default_factory=dict)


@dataclass
class IntentionHypothesis:
    intention_type: str
    probability: float
    supporting_actions: List[str] = field(default_factory=list)


class IntentionPredictor:
    def __init__(self, history_size: int = 200):
        self.history_size = history_size
        self.actions: List[Action] = []
        self.hypotheses: Dict[str, IntentionHypothesis] = {}
        self.action_transitions: Dict[str, Dict[str, int]] = {}
        self.intention_priors: Dict[str, float] = {}

    def record_action(self, action: Action) -> None:
        self.actions.append(action)
        if len(self.actions) > self.history_size:
            self.actions = self.actions[-self.history_size :]
        if self.actions:
            prev = self.actions[-2].action_type if len(self.actions) >= 2 else None
            curr = action.action_type
            if prev is not None:
                if prev not in self.action_transitions:
                    self.action_transitions[prev] = {}
                self.action_transitions[prev][curr] = self.action_transitions[prev].get(curr, 0) + 1

    def predict(self, recent_actions: int = 5) -> List[IntentionHypothesis]:
        if not self.actions:
            return []
        recent = self.actions[-recent_actions:]
        action_types = [a.action_type for a in recent]
        scores: Dict[str, float] = {}
        for at in action_types:
            scores[at] = scores.get(at, 0.0) + 1.0
        total = sum(scores.values())
        if total == 0:
            return []
        for intention in scores:
            scores[intention] /= total
        results = []
        for intention, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            supporting = [a.target for a in recent if a.action_type == intention]
            hypothesis = IntentionHypothesis(intention_type=intention, probability=score, supporting_actions=supporting)
            self.hypotheses[intention] = hypothesis
            results.append(hypothesis)
        return results

    def top_hypotheses(self, k: int = 3) -> List[IntentionHypothesis]:
        return sorted(self.hypotheses.values(), key=lambda h: h.probability, reverse=True)[:k]

    def intention_entropy(self) -> float:
        if not self.hypotheses:
            return 0.0
        probs = [h.probability for h in self.hypotheses.values()]
        return -sum(p * math.log(p) for p in probs if p > 0.0)

    def update_hypothesis_evidence(self, intention_type: str, evidence_strength: float) -> None:
        strength = max(0.0, min(1.0, evidence_strength))
        if intention_type not in self.hypotheses:
            self.hypotheses[intention_type] = IntentionHypothesis(intention_type=intention_type, probability=0.0, supporting_actions=[])
        self.hypotheses[intention_type].probability = max(0.0, min(1.0, self.hypotheses[intention_type].probability + strength * 0.1))
