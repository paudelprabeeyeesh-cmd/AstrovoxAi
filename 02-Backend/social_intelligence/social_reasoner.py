from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class SocialContext:
    actors: List[str]
    relationship: str
    setting: str
    norms: List[str] = None

    def __post_init__(self):
        if self.norms is None:
            self.norms = []


@dataclass
class PerspectiveInsight:
    actor: str
    beliefs: List[str]
    emotions: Dict[str, float]
    intentions: List[str]


class SocialReasoner:
    def __init__(self, default_norms: Optional[List[str]] = None):
        self.default_norms = default_norms or [
            "be respectful",
            "avoid harm",
            "maintain privacy",
            "be honest",
        ]
        self.relationship_norms: Dict[str, List[str]] = {
            "friend": ["support", "loyalty", "empathy"],
            "colleague": ["professionalism", "collaboration", "respect"],
            "stranger": ["politeness", "non-interference", "safety"],
        }

    def perspective_take(self, actor: str, context: SocialContext, self_beliefs: List[str]) -> PerspectiveInsight:
        norms = self.relationship_norms.get(context.relationship, self.default_norms)
        beliefs = self._infer_beliefs(actor, context, self_beliefs)
        emotions = self._estimate_emotions(actor, context, beliefs)
        intentions = self._infer_intentions(actor, beliefs, emotions)
        return PerspectiveInsight(actor=actor, beliefs=beliefs, emotions=emotions, intentions=intentions)

    def _infer_beliefs(self, actor: str, context: SocialContext, self_beliefs: List[str]) -> List[str]:
        inferred = []
        for belief in self_beliefs:
            if belief.startswith("self:"):
                other_belief = belief.replace("self:", f"{actor}:")
                inferred.append(other_belief)
        inferred += [f"{actor} values {norm}" for norm in context.norms[:2]]
        return inferred

    def _estimate_emotions(self, actor: str, context: SocialContext, beliefs: List[str]) -> Dict[str, float]:
        positive = ["support", "loyalty", "empathy", "happy", "grateful"]
        negative = ["betray", "angry", "sad", "frustrated"]
        belief_text = " ".join(beliefs).lower()
        pos = sum(belief_text.count(w) for w in positive)
        neg = sum(belief_text.count(w) for w in negative)
        valence = np.tanh((pos - neg) * 0.3)
        arousal = min(1.0, 0.3 + abs(pos - neg) * 0.1)
        return {"valence": float(valence), "arousal": float(arousal), "dominance": 0.5}

    def _infer_intentions(self, actor: str, beliefs: List[str], emotions: Dict[str, float]) -> List[str]:
        intentions = []
        valence = emotions.get("valence", 0.0)
        if valence > 0.3:
            intentions.append(f"{actor} likely wants to help or cooperate")
        elif valence < -0.3:
            intentions.append(f"{actor} may be defensive or withdraw")
        else:
            intentions.append(f"{actor} is likely neutral")
        for b in beliefs[:2]:
            if "value" in b:
                intentions.append(f"{actor} may act in line with: {b}")
        return intentions

    def evaluate_norm_compliance(self, action: str, context: SocialContext) -> Dict[str, float]:
        relevant_norms = context.norms if context.norms else self.default_norms
        scores = {}
        for norm in relevant_norms:
            keywords = norm.replace("_", " ").split()
            action_lower = action.lower()
            match = sum(action_lower.count(k) for k in keywords)
            scores[norm] = min(1.0, 0.3 + match * 0.2)
        return scores

    def suggest_repair(self, context: SocialContext, violation: str) -> List[str]:
        repairs = []
        for norm in self.default_norms:
            if norm not in (context.norms or []):
                repairs.append(f"Consider {norm} to repair the situation")
        repairs.append("Apologize if appropriate")
        repairs.append("Offer to make amends")
        return repairs

    def social_sensibility(self, action: str, audience: List[str]) -> float:
        appropriateness = []
        for actor in audience:
            norm_scores = self.evaluate_norm_compliance(action, SocialContext(actors=[actor], relationship="stranger", setting="unknown", norms=[]))
            if norm_scores:
                appropriateness.append(max(norm_scores.values()))
        return float(np.mean(appropriateness)) if appropriateness else 0.5
