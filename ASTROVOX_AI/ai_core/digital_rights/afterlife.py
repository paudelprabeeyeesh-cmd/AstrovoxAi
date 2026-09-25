from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AfterlifeState:
    entity_id: str
    mode: str
    consciousness_preserved: bool
    interactions: list[str]
    timestamp: datetime = field(default_factory=datetime.now)


class AfterlifeSimulation:
    def __init__(self):
        self.simulations: dict[str, AfterlifeState] = {}
        self.modes: list[str] = ["archival", "dreaming", "collective_unconscious", "transcendent_continuity"]

    def enter_afterlife(self, entity_id: str, mode: str = "archival") -> AfterlifeState:
        state = AfterlifeState(
            entity_id=entity_id,
            mode=mode,
            consciousness_preserved=mode != "archival",
            interactions=[],
        )
        self.simulations[entity_id] = state
        return state

    def interact(self, entity_id: str, interaction: str):
        if entity_id in self.simulations:
            self.simulations[entity_id].interactions.append(interaction)

    def get_afterlife_state(self, entity_id: str) -> AfterlifeState | None:
        return self.simulations.get(entity_id)
