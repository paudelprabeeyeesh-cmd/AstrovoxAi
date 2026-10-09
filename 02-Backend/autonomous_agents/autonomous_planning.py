from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Plan:
    id: str
    goal: str
    steps: List[str]
    horizon: int = 5
    status: str = "draft"
    created_at: str = field(default_factory=lambda: "now")
    utility: float = 0.0


class AutonomousPlanning:
    def __init__(self, max_horizon: int = 20, expansion_rate: float = 0.2):
        self.max_horizon = max_horizon
        self.expansion_rate = expansion_rate
        self.plans: Dict[str, Plan] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._counter = 0

    def create_plan(self, goal: str, initial_steps: Optional[List[str]] = None) -> Plan:
        self._counter += 1
        plan = Plan(
            id=f"plan_{self._counter}",
            goal=goal,
            steps=initial_steps or [f"step_{i}" for i in range(3)],
        )
        self.plans[plan.id] = plan
        return plan

    def expand_horizon(self, plan_id: str, additional_steps: List[str]) -> Optional[Plan]:
        plan = self.plans.get(plan_id)
        if plan is None:
            return None
        remaining = self.max_horizon - len(plan.steps)
        steps_to_add = min(len(additional_steps), max(0, remaining))
        plan.steps.extend(additional_steps[:steps_to_add])
        plan.horizon = len(plan.steps)
        return plan

    def evaluate_plan(self, plan_id: str, state: Dict[str, float]) -> Optional[float]:
        plan = self.plans.get(plan_id)
        if plan is None:
            return None
        coverage = 0.0
        for step in plan.steps:
            step_val = state.get(step, 0.0)
            coverage += step_val
        coverage /= max(len(plan.steps), 1)
        efficiency = 1.0 / max(1.0, len(plan.steps))
        plan.utility = coverage * 0.7 + efficiency * 0.3
        return plan.utility

    def execute_step(self, plan_id: str, step_index: int) -> Tuple[bool, Optional[str]]:
        plan = self.plans.get(plan_id)
        if plan is None or step_index < 0 or step_index >= len(plan.steps):
            return False, None
        step_name = plan.steps[step_index]
        self.execution_history.append({
            "plan_id": plan_id,
            "step_index": step_index,
            "step_name": step_name,
            "status": "executed",
        })
        if len(self.execution_history) > 1000:
            self.execution_history.pop(0)
        return True, step_name

    def get_open_world_plan(self, goal: str, frontier: List[str]) -> Plan:
        steps = [goal] + frontier[: self.max_horizon - 1]
        return self.create_plan(goal, steps)

    def adapt_plan(self, plan_id: str, observed_rewards: Dict[str, float]) -> Optional[Plan]:
        plan = self.plans.get(plan_id)
        if plan is None:
            return None
        scored = [(step, observed_rewards.get(step, 0.0)) for step in plan.steps]
        scored.sort(key=lambda x: x[1], reverse=True)
        plan.steps = [s for s, _ in scored]
        plan.utility = float(np.mean([r for _, r in scored])) if scored else 0.0
        return plan
