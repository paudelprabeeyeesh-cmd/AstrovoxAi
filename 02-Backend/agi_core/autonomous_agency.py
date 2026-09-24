from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class AgencyState:
    goal: str
    action: str
    confidence: float
    autono_level: float


class AutonomousAgency:
    def __init__(self):
        self.state: Optional[AgencyState] = None
        self.goal_history: List[str] = []
        self.action_history: List[str] = []

    def set_goal(self, goal: str, autono_level: float = 0.8) -> AgencyState:
        self.state = AgencyState(goal=goal, action="", confidence=0.5, autono_level=autono_level)
        self.goal_history.append(goal)
        return self.state

    def choose_action(self, actions: List[str], context: str = "") -> AgencyState:
        if not self.state:
            self.set_goal("unknown")
        if not actions:
            return self.state
        scores = [np.random.uniform(0.4, 1.0) for _ in actions]
        best_idx = int(np.argmax(scores))
        self.state.action = actions[best_idx]
        self.state.confidence = scores[best_idx]
        self.action_history.append(self.state.action)
        return self.state

    def self_direct(self, feedback: str) -> AgencyState:
        if not self.state:
            self.set_goal("self_directed")
        self.state.confidence = max(0.0, min(1.0, self.state.confidence + 0.1))
        return self.state

    def evaluate_agency(self) -> Dict[str, float]:
        if not self.state:
            return {"goal_clarity": 0.0, "action_independence": 0.0, "autonomy": 0.0}
        goal_clarity = 1.0 if self.state.goal else 0.0
        action_independence = self.state.autono_level
        return {"goal_clarity": goal_clarity, "action_independence": action_independence, "autonomy": action_independence}
