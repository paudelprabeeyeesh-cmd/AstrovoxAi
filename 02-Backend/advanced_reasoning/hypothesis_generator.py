from dataclasses import dataclass, field
from typing import List


@dataclass
class Observation:
    id: str
    description: str
    context: str = ""


@dataclass
class Hypothesis:
    id: str
    statement: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.5
    testable: bool = True


class HypothesisGenerator:
    def __init__(self):
        self.observations: dict = {}
        self.hypotheses: List[Hypothesis] = []

    def add_observation(self, observation: Observation) -> None:
        self.observations[observation.id] = observation

    def generate(self, observation_ids: List[str], template: str = "{cause} causes {effect}") -> List[Hypothesis]:
        if not observation_ids:
            return []
        descs = [self.observations[oid].description for oid in observation_ids if oid in self.observations]
        generated: List[Hypothesis] = []
        for i, desc in enumerate(descs):
            words = desc.lower().split()
            cause = words[0] if words else "unknown"
            effect = words[-1] if words else "unknown"
            statement = template.replace("{cause}", cause).replace("{effect}", effect)
            hid = f"h-{len(self.hypotheses) + i + 1}"
            h = Hypothesis(id=hid, statement=statement, evidence_ids=observation_ids, confidence=0.5)
            generated.append(h)
            self.hypotheses.append(h)
        return generated

    def refine(self, hypothesis_id: str, new_evidence_ids: List[str]) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.id == hypothesis_id:
                h.evidence_ids.extend(new_evidence_ids)
                h.confidence = min(1.0, h.confidence + 0.1 * len(new_evidence_ids))
                return h
        return None
