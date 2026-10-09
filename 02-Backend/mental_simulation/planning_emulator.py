from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Plan:
    goal: str
    steps: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    plan: Plan
    success: bool
    steps_completed: int
    outcomes: List[str] = field(default_factory=list)


class PlanningEmulator:
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self.history: List[ExecutionResult] = []

    def emulate(self, goal: str, context: Dict[str, Any]) -> ExecutionResult:
        plan = Plan(goal=goal)
        steps = context.get("steps", [])
        plan.steps = steps[: self.max_steps]
        executed = 0
        outcomes: List[str] = []
        success = True
        for step in plan.steps:
            expected = context.get("expected_success_rate", 0.5)
            success = expected >= 0.5
            executed += 1
            outcomes.append(f"executed_{step}")
        result = ExecutionResult(plan=plan, success=success, steps_completed=executed, outcomes=outcomes)
        self.history.append(result)
        return result

    def replan(self, previous: ExecutionResult, feedback: Dict[str, Any]) -> ExecutionResult:
        new_goal = previous.plan.goal
        excluded = set(feedback.get("failed_steps", []))
        remaining = [s for s in previous.plan.steps if s not in excluded]
        return self.emulate(new_goal, {"steps": remaining, "expected_success_rate": feedback.get("expected_success_rate", 0.5)})
