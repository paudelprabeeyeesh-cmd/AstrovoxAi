import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MentalState:
    beliefs: dict[str, Any] = field(default_factory=dict)
    desires: list[str] = field(default_factory=list)
    intentions: list[str] = field(default_factory=list)
    emotions: dict[str, float] = field(default_factory=dict)


class TheoryOfMindModel:
    def __init__(self):
        self.agents: dict[str, MentalState] = {}

    def register_agent(self, agent_id: str, state: MentalState) -> None:
        self.agents[agent_id] = state

    def infer_state(self, agent_id: str, observations: list[str]) -> MentalState:
        if agent_id in self.agents:
            return self.agents[agent_id]
        state = MentalState(beliefs={"inferred": True})
        self.agents[agent_id] = state
        return state
