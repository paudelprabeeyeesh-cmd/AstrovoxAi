import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Belief:
    proposition: str
    confidence: float
    evidence_count: int
    last_updated: float
    sources: List[str] = field(default_factory=list)


@dataclass
class BeliefState:
    beliefs: Dict[str, Belief]
    entropy: float
    confidence_summary: Dict[str, float]


class BeliefTracker:
    def __init__(self, history_size: int = 200):
        self.history_size = history_size
        self.beliefs: Dict[str, Belief] = {}
        self.evidence_log: Dict[str, List[Tuple[float, str]]] = {}

    def observe(self, proposition: str, confidence: float, source: str, timestamp: float) -> Belief:
        if proposition not in self.beliefs:
            self.beliefs[proposition] = Belief(
                proposition=proposition, confidence=confidence, evidence_count=0, last_updated=timestamp, sources=[]
            )
            self.evidence_log[proposition] = []
        belief = self.beliefs[proposition]
        belief.confidence = self._update_confidence(belief.confidence, confidence)
        belief.evidence_count += 1
        belief.last_updated = timestamp
        if source not in belief.sources:
            belief.sources.append(source)
        self.evidence_log[proposition].append((timestamp, source))
        if len(self.evidence_log[proposition]) > self.history_size:
            self.evidence_log[proposition] = self.evidence_log[proposition][-self.history_size :]
        return belief

    def _update_confidence(self, current: float, new_evidence: float) -> float:
        evidence = max(0.0, min(1.0, new_evidence))
        return max(0.0, min(1.0, (current + evidence) / 2.0))

    def get_belief_state(self) -> BeliefState:
        if not self.beliefs:
            return BeliefState(beliefs={}, entropy=0.0, confidence_summary={})
        confidences = [b.confidence for b in self.beliefs.values()]
        entropy = self._entropy(confidences)
        summary = {prop: b.confidence for prop, b in self.beliefs.items()}
        return BeliefState(beliefs=dict(self.beliefs), entropy=entropy, confidence_summary=summary)

    def _entropy(self, values: List[float]) -> float:
        if not values:
            return 0.0
        avg = sum(values) / len(values)
        if avg <= 0.0 or avg >= 1.0:
            return 0.0
        return -avg * math.log(avg) - (1.0 - avg) * math.log(1.0 - avg)

    def most_confident(self, top_k: int = 5) -> List[Belief]:
        return sorted(self.beliefs.values(), key=lambda b: b.confidence, reverse=True)[:top_k]

    def least_confident(self, top_k: int = 5) -> List[Belief]:
        return sorted(self.beliefs.values(), key=lambda b: b.confidence)[:top_k]

    def conflicting_beliefs(self, threshold: float = 0.3) -> List[Tuple[str, str]]:
        props = list(self.beliefs.keys())
        conflicts = []
        for i in range(len(props)):
            for j in range(i + 1, len(props)):
                b1 = self.beliefs[props[i]]
                b2 = self.beliefs[props[j]]
                if abs(b1.confidence - b2.confidence) < threshold and b1.evidence_count > 2 and b2.evidence_count > 2:
                    conflicts.append((props[i], props[j]))
        return conflicts
