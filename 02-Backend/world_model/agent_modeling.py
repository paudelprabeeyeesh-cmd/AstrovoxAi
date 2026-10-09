from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class Belief:
    proposition: str
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)
    last_updated: int = 0

    def update(self, new_confidence: float, evidence_id: str) -> None:
        self.confidence = 0.7 * self.confidence + 0.3 * max(0.0, min(1.0, new_confidence))
        self.evidence.append(evidence_id)
        self.last_updated += 1


@dataclass
class Intention:
    action: str
    target: Optional[str] = None
    priority: float = 0.5
    utility: float = 0.0


class AgentModel:
    def __init__(self, agent_id: str, traits: Dict[str, float] = None):
        self.agent_id = agent_id
        self.traits = traits or {"risk": 0.5, "cooperation": 0.5, "speed": 0.5}
        self.beliefs: Dict[str, Belief] = {}
        self.intentions: List[Intention] = []
        self.action_history: List[Dict[str, Any]] = []

    def set_belief(self, proposition: str, confidence: float, evidence: str = "") -> None:
        if proposition not in self.beliefs:
            self.beliefs[proposition] = Belief(proposition=proposition)
        self.beliefs[proposition].update(confidence, evidence)

    def get_belief(self, proposition: str) -> Optional[Belief]:
        return self.beliefs.get(proposition)

    def add_intention(self, action: str, target: str = None, priority: float = 0.5, utility: float = 0.0) -> None:
        intention = Intention(action=action, target=target, priority=priority, utility=utility)
        self.intentions.append(intention)
        self.intentions.sort(key=lambda i: (i.priority, i.utility), reverse=True)

    def select_action(self) -> Optional[Intention]:
        if not self.intentions:
            return None
        return self.intentions[0]

    def execute(self, environment_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        intention = self.select_action()
        if intention is None:
            return None
        success_prob = 0.5 + 0.5 * self.traits.get("speed", 0.5)
        success = np.random.rand() < success_prob
        result = {
            "agent_id": self.agent_id,
            "action": intention.action,
            "target": intention.target,
            "success": success,
            "timestamp": len(self.action_history),
        }
        self.action_history.append(result)
        if success:
            self.intentions.pop(0)
        return result

    def belief_distribution(self) -> Dict[str, float]:
        return {p: b.confidence for p, b in self.beliefs.items()}
