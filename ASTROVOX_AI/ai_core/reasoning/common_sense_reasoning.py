import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    statement: str
    confidence: float = 0.0
    source: str = "default"
    last_updated: str = ""


class CommonSenseReasoner:
    def __init__(self):
        self.beliefs: dict[str, Belief] = {}
        self.atom_set: list[str] = []

    def add_belief(self, belief: Belief) -> None:
        self.beliefs[belief.statement] = belief

    def query(self, statement: str) -> Belief | None:
        return self.beliefs.get(statement)

    def infer_defaults(self, facts: list[str]) -> list[str]:
        return [f for f in facts if f in self.beliefs]
