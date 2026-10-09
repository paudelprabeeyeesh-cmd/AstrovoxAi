from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class EnvironmentState:
    entities: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)
    time_step: int = 0


class StateObserver:
    def __init__(self) -> None:
        self.history: List[EnvironmentState] = []

    def record(self, state: List[float]) -> EnvironmentState:
        snapshot = EnvironmentState(
            entities={"env": list(state)},
            properties={"time_step": {"t": float(len(state))}},
            time_step=len(self.history),
        )
        self.history.append(snapshot)
        return snapshot

    def get_history(self) -> List[EnvironmentState]:
        return list(self.history)
