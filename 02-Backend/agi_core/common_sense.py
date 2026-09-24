from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class WorldFact:
    subject: str
    relation: str
    object: str
    confidence: float
    source: str = "default"


@dataclass
class DefaultAssumption:
    context: str
    assumption: str
    confidence: float
    exception: Optional[str] = None


class CommonSenseEngine:
    def __init__(self):
        self.facts: List[WorldFact] = []
        self.defaults: Dict[str, DefaultAssumption] = {}
        self.world_knowledge: Dict[str, float] = {}

    def add_fact(self, subject: str, relation: str, object_: str, confidence: float = 0.8, source: str = "default") -> WorldFact:
        fact = WorldFact(subject=subject, relation=relation, object=object_, confidence=confidence, source=source)
        self.facts.append(fact)
        key = f"{subject}_{relation}_{object_}"
        self.world_knowledge[key] = confidence
        return fact

    def query(self, subject: str, relation: str) -> List[WorldFact]:
        return [f for f in self.facts if f.subject == subject and f.relation == relation]

    def apply_default(self, context: str, fallback: str = "unknown") -> str:
        if context in self.defaults:
            return self.defaults[context].assumption
        return fallback

    def register_default(self, context: str, assumption: str, confidence: float, exception: Optional[str] = None) -> DefaultAssumption:
        da = DefaultAssumption(context=context, assumption=assumption, confidence=confidence, exception=exception)
        self.defaults[context] = da
        return da

    def detect_exception(self, context: str, observation: str) -> bool:
        if context not in self.defaults:
            return False
        da = self.defaults[context]
        return da.exception is not None and da.exception.lower() in observation.lower()

    def consistency_check(self, new_fact: WorldFact) -> float:
        matching = [f for f in self.facts if f.subject == new_fact.subject and f.relation == new_fact.relation]
        if not matching:
            return 1.0
        similarities = [1.0 if m.object == new_fact.object else 0.0 for m in matching]
        return float(np.mean(similarities))
