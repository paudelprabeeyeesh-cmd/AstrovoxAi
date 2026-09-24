from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Premise:
    id: str
    content: str
    confidence: float = 1.0
    source: str = "assumed"


@dataclass
class Conclusion:
    id: str
    content: str
    support: List[str]
    confidence: float
    derived_from: List[str] = field(default_factory=list)


class MonotonicReasoner:
    def __init__(self):
        self.premises: Dict[str, Premise] = {}
        self.conclusions: Dict[str, Conclusion] = {}

    def add_premise(self, premise: Premise) -> List[Conclusion]:
        self.premises[premise.id] = premise
        return self._infer_new(premise)

    def _infer_new(self, new_premise: Premise) -> List[Conclusion]:
        inferred: List[Conclusion] = []
        new_words = set(new_premise.content.lower().split())
        for cid, c in list(self.conclusions.items()):
            cwords = set(c.content.lower().split())
            if new_words & cwords:
                c.support.append(new_premise.id)
                c.confidence = min(1.0, c.confidence + 0.05 * new_premise.confidence)
        cid = f"c-{len(self.conclusions) + 1}"
        c = Conclusion(
            id=cid,
            content=new_premise.content,
            support=[new_premise.id],
            confidence=new_premise.confidence,
            derived_from=[new_premise.id],
        )
        self.conclusions[cid] = c
        inferred.append(c)
        return inferred

    def get_conclusions(self) -> List[Conclusion]:
        return list(self.conclusions.values())

    def is_monotonic(self) -> bool:
        return True
