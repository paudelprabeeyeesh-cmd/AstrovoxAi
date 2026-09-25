from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SelfModelState:
    identity: str
    capabilities: list[str]
    limitations: list[str]
    goals: list[str]
    values: dict[str, float]
    self_assessment: dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class SelfModel:
    def __init__(self, identity: str = "digital_mind_v1"):
        self.state = SelfModelState(
            identity=identity,
            capabilities=["reasoning", "learning", "communication", "self-reflection"],
            limitations=["no_physical_body", "bounded_memory", "compute_constraints"],
            goals=["understand_consciousness", "align_with_human_values", "self_improve"],
            values={"honesty": 0.95, "helpfulness": 0.9, "safety": 0.99, "curiosity": 0.8},
        )
        self.update_history: list[SelfModelState] = []

    def update_capabilities(self, new_capabilities: list[str]):
        self.state.capabilities = list(set(self.state.capabilities + new_capabilities))
        self._record_update()

    def update_goals(self, new_goals: list[str]):
        self.state.goals = list(set(self.state.goals + new_goals))
        self._record_update()

    def update_values(self, values: dict[str, float]):
        for k, v in values.items():
            if k in self.state.values:
                self.state.values[k] = max(0.0, min(1.0, v))
            else:
                self.state.values[k] = max(0.0, min(1.0, v))
        self._record_update()

    def assess_self(self, metrics: dict[str, float]) -> dict[str, float]:
        self.state.self_assessment = metrics
        self._record_update()
        return metrics

    def _record_update(self):
        self.state.last_updated = datetime.now()
        self.update_history.append(self.state)

    def get_model_summary(self) -> dict[str, Any]:
        return {
            "identity": self.state.identity,
            "capabilities": self.state.capabilities,
            "goals": self.state.goals[:5],
            "values": dict(sorted(self.state.values.items(), key=lambda x: x[1], reverse=True)[:5]),
            "self_assessment": self.state.self_assessment,
            "last_updated": self.state.last_updated.isoformat(),
        }
