from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class MentalState:
    beliefs: Dict[str, float] = field(default_factory=dict)
    desires: List[str] = field(default_factory=list)
    intentions: List[str] = field(default_factory=list)


@dataclass
class TheoryOfMindHypothesis:
    agent_id: str
    mental_state: MentalState
    confidence: float = 0.5


class TheoryOfMind:
    def __init__(self):
        self.hypotheses: Dict[str, TheoryOfMindHypothesis] = {}
        self.observations: List[Dict[str, Any]] = []

    def observe(self, agent_id: str, action: str, context: Dict[str, Any]) -> None:
        self.observations.append({"agent_id": agent_id, "action": action, "context": context})
        if agent_id not in self.hypotheses:
            self.hypotheses[agent_id] = TheoryOfMindHypothesis(
                agent_id=agent_id,
                mental_state=MentalState(),
            )

    def infer_belief(self, agent_id: str, proposition: str) -> float:
        hypothesis = self.hypotheses.get(agent_id)
        if hypothesis is None:
            return 0.5
        return hypothesis.mental_state.beliefs.get(proposition, 0.5)

    def infer_intention(self, agent_id: str) -> Optional[str]:
        hypothesis = self.hypotheses.get(agent_id)
        if hypothesis is None or not hypothesis.mental_state.intentions:
            return None
        return hypothesis.mental_state.intentions[-1]

    def predict_next_action(self, agent_id: str) -> Optional[str]:
        intention = self.infer_intention(agent_id)
        if intention is None:
            return None
        return intention

    def update_hypothesis(self, agent_id: str, belief_key: str, confidence: float) -> None:
        if agent_id not in self.hypotheses:
            self.hypotheses[agent_id] = TheoryOfMindHypothesis(agent_id=agent_id, mental_state=MentalState())
        self.hypotheses[agent_id].mental_state.beliefs[belief_key] = max(0.0, min(1.0, confidence))
        self.hypotheses[agent_id].confidence = float(np.mean(list(self.hypotheses[agent_id].mental_state.beliefs.values()))) if self.hypotheses[agent_id].mental_state.beliefs else 0.5


class MentalSimulator:
    def __init__(self, theory_of_mind: TheoryOfMind):
        self.theory_of_mind = theory_of_mind
        self.simulations: List[Dict[str, Any]] = []

    def simulate_plan(self, agent_id: str, actions: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        plan = []
        for action in actions:
            likelihood = self.theory_of_mind.infer_belief(agent_id, f"will_{action}")
            plan.append({"action": action, "likelihood": likelihood, "context": context})
        return plan

    def simulate_dialogue(self, agent_id: str, turns: int = 3) -> List[Dict[str, Any]]:
        dialogue = []
        for turn in range(turns):
            intention = self.theory_of_mind.infer_intention(agent_id)
            dialogue.append({"turn": turn, "intention": intention, "speaker": agent_id})
        return dialogue
