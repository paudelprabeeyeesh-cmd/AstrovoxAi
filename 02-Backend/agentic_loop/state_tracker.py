from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LoopStep:
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoopState:
    query: str
    steps: List[LoopStep] = field(default_factory=list)
    status: str = "running"
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateTracker:
    def __init__(self) -> None:
        self.state = LoopState(query="")

    def initialize(self, query: str) -> None:
        self.state = LoopState(query=query)

    def add_step(self, step: LoopStep) -> None:
        self.state.steps.append(step)

    def update_status(self, status: str) -> None:
        self.state.status = status

    def set_metadata(self, key: str, value: Any) -> None:
        self.state.metadata[key] = value

    def get_history(self) -> List[LoopStep]:
        return list(self.state.steps)

    def reset(self) -> None:
        self.state = LoopState(query="")
