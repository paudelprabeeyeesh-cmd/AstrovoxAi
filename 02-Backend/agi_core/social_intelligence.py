from dataclasses import dataclass
from typing import Dict, List
import numpy as np


@dataclass
class SocialModel:
    entity: str
    mental_state: Dict[str, float]
    relationship: str
    trust: float


class SocialIntelligence:
    def __init__(self):
        self.models: Dict[str, SocialModel] = {}
        self.interaction_history: List[Dict[str, float]] = []

    def infer_mental_state(self, entity: str, observations: List[str]) -> Dict[str, float]:
        if entity not in self.models:
            self.models[entity] = SocialModel(entity=entity, mental_state={"valence": 0.0, "arousal": 0.0, "competence": 0.5}, relationship="unknown", trust=0.5)
        state = self.models[entity].mental_state
        valence = sum(1.0 if "positive" in o.lower() else -1.0 for o in observations) / max(len(observations), 1)
        state["valence"] = max(-1.0, min(1.0, valence))
        return state

    def build_relationship(self, entity: str, relationship_type: str) -> None:
        if entity not in self.models:
            self.models[entity] = SocialModel(entity=entity, mental_state={"valence": 0.0, "arousal": 0.0, "competence": 0.5}, relationship=relationship_type, trust=0.5)
        else:
            self.models[entity].relationship = relationship_type

    def cooperate(self, entities: List[str], task: str) -> Dict[str, float]:
        if not entities:
            return {}
        scores = {}
        for e in entities:
            if e not in self.models:
                self.models[e] = SocialModel(entity=e, mental_state={"valence": 0.0, "arousal": 0.0, "competence": 0.5}, relationship="unknown", trust=0.5)
            scores[e] = self.models[e].trust * 0.7 + 0.3
        self.interaction_history.append(scores)
        return scores

    def negotiate(self, entity: str, target_state: Dict[str, float]) -> Dict[str, float]:
        if entity not in self.models:
            self.models[entity] = SocialModel(entity=entity, mental_state={"valence": 0.0, "arousal": 0.0, "competence": 0.5}, relationship="unknown", trust=0.5)
        proposed = dict(self.models[entity].mental_state)
        for k, v in target_state.items():
            proposed[k] = proposed.get(k, 0.0) * 0.5 + v * 0.5
        return proposed

    def get_trust_report(self) -> Dict[str, float]:
        if not self.models:
            return {"mean_trust": 0.0, "max_trust": 0.0}
        trusts = [m.trust for m in self.models.values()]
        return {"mean_trust": float(np.mean(trusts)), "max_trust": float(np.max(trusts))}
