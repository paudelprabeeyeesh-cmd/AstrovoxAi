import logging
from typing import Any

from app.agi_reasoning import AGIReasoningService
from app.decomposition import TaskDecomposer
from app.planning import PlanningEngine
from app.recursive_planning import RecursivePlanningService
from app.self_evolution import SelfEvolutionService

logger = logging.getLogger(__name__)


class AGIOrchestrator:
    def __init__(self) -> None:
        self.reasoning = AGIReasoningService()
        self.self_evolution = SelfEvolutionService()
        self.planning = RecursivePlanningService()
        self.task_decomposer = TaskDecomposer()
        self.planning_engine = PlanningEngine()

    def execute_goal(self, goal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        plan_result = self.planning.create_plan(goal, context=context)
        plan_id = plan_result.get("plan_id")
        decomposed = self.task_decomposer.decompose_goal(goal)
        reasoning_summary = self.reasoning.query("causal_reasoning", f"How to achieve: {goal}")
        return {
            "goal": goal,
            "plan_id": plan_id,
            "decomposed_goal_id": decomposed.goal_id,
            "reasoning": reasoning_summary,
            "status": "orchestrated",
        }

    def improve(self, target: str, feedback: str) -> dict[str, Any]:
        improvement = self.self_evolution.act("self_modifying_code", "generate_patch_from_feedback", {"module_name": target, "feedback": feedback})
        return {"target": target, "improvement": improvement}

    def reason_about(self, engine: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.reasoning.reason(engine, payload)

    def evolve(self, module: str, action: str, args: dict[str, Any]) -> dict[str, Any]:
        return self.self_evolution.act(module, action, args)


_agi_orchestrator = AGIOrchestrator()
