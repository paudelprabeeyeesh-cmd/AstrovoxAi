import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    content: str
    confidence: float = 1.0
    source: str = "observed"


@dataclass
class Desire:
    content: str
    intensity: float = 1.0
    urgency: float = 0.0


@dataclass
class Intention:
    content: str
    plan: list[str] = field(default_factory=list)
    commitment: float = 1.0


@dataclass
class MentalState:
    beliefs: dict[str, Belief] = field(default_factory=dict)
    desires: dict[str, Desire] = field(default_factory=dict)
    intentions: dict[str, Intention] = field(default_factory=dict)
    emotions: dict[str, float] = field(default_factory=dict)
    attention: str = ""


class TheoryOfMindEngine:
    def __init__(self):
        self.agents: dict[str, MentalState] = {}
        self.self_state = MentalState()
        self.mentalizing_accuracy: dict[str, float] = {}

    def register_agent(self, agent_id: str, initial_state: MentalState | None = None) -> None:
        self.agents[agent_id] = initial_state or MentalState()
        self.mentalizing_accuracy[agent_id] = 0.5
        logger.info("Registered agent: %s", agent_id)

    def observe(self, agent_id: str, observation: str) -> dict[str, Any]:
        if agent_id not in self.agents:
            self.register_agent(agent_id)

        state = self.agents[agent_id]
        lower = observation.lower()

        if "wants" in lower:
            state.desires[observation] = Desire(content=observation, intensity=0.8)
        elif "believes" in lower:
            state.beliefs[observation] = Belief(content=observation, confidence=0.7)
        elif "intends" in lower:
            state.intentions[observation] = Intention(content=observation, plan=[observation])

        logger.info("Observed %s: %s", agent_id, observation)
        return {"status": "updated", "agent_id": agent_id}

    def perspective_take(self, agent_id: str, scenario: str) -> dict[str, Any]:
        if agent_id not in self.agents:
            return {"error": "Unknown agent"}

        state = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "predicted_beliefs": list(state.beliefs.keys()),
            "predicted_desires": list(state.desires.keys()),
            "predicted_intentions": list(state.intentions.keys()),
            "scenario": scenario,
        }

    def update_mentalizing_accuracy(self, agent_id: str, delta: float):
        if agent_id not in self.mentalizing_accuracy:
            self.mentalizing_accuracy[agent_id] = 0.5
        self.mentalizing_accuracy[agent_id] = max(0.0, min(1.0, self.mentalizing_accuracy[agent_id] + delta))

    def get_mental_state(self, agent_id: str) -> dict[str, Any]:
        if agent_id not in self.agents:
            return {"error": "Unknown agent"}

        state = self.agents[agent_id]
        return {
            "beliefs": {k: {"content": v.content, "confidence": v.confidence} for k, v in state.beliefs.items()},
            "desires": {k: {"content": v.content, "intensity": v.intensity} for k, v in state.desires.items()},
            "intentions": {k: {"content": v.content, "commitment": v.commitment} for k, v in state.intentions.items()},
            "emotions": state.emotions,
            "accuracy": self.mentalizing_accuracy.get(agent_id, 0.5),
        }
