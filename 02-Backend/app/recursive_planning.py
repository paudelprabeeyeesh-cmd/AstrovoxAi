import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    step_id: str
    description: str
    sub_steps: list["PlanStep"] = field(default_factory=list)
    status: str = "pending"
    estimated_cost: float = 0.0
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class RecursivePlan:
    plan_id: str
    goal: str
    root_step: PlanStep
    status: str = "active"
    iteration: int = 0
    max_depth: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class RecursivePlanningService:
    def __init__(self) -> None:
        self._plans: dict[str, RecursivePlan] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def create_plan(self, goal: str, max_depth: int = 5, context: dict[str, Any] | None = None) -> dict[str, Any]:
        plan_id = str(uuid.uuid4())
        root = self._decompose(goal, depth=0, max_depth=max_depth)
        plan = RecursivePlan(plan_id=plan_id, goal=goal, root_step=root, max_depth=max_depth, metadata={"context": context or {}})
        self._plans[plan_id] = plan
        logger.info("Created recursive plan %s for goal: %s", plan_id, goal[:80])
        return {"plan_id": plan_id, "goal": goal, "max_depth": max_depth, "status": "created"}

    def refine(self, plan_id: str, feedback: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {"plan_id": plan_id, "status": "not_found"}
        plan.iteration += 1
        plan.root_step = self._decompose(plan.goal, depth=0, max_depth=plan.max_depth, feedback=feedback)
        logger.info("Refined plan %s (iteration %d)", plan_id, plan.iteration)
        return {"plan_id": plan_id, "status": "refined", "iteration": plan.iteration}

    def execute_step(self, plan_id: str, step_id: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {"plan_id": plan_id, "status": "not_found"}
        step = self._find_step(plan.root_step, step_id)
        if not step:
            return {"plan_id": plan_id, "step_id": step_id, "status": "not_found"}
        if step.sub_steps:
            return {"plan_id": plan_id, "step_id": step_id, "status": "delegated", "sub_steps": len(step.sub_steps)}
        step.status = "completed"
        return {"plan_id": plan_id, "step_id": step_id, "status": "completed"}

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        return {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "status": plan.status,
            "iteration": plan.iteration,
            "max_depth": plan.max_depth,
            "root_step": self._serialize_step(plan.root_step),
            "created_at": plan.created_at,
        }

    def list_plans(self) -> list[str]:
        return list(self._plans.keys())

    def _decompose(self, description: str, depth: int, max_depth: int, feedback: str = "") -> PlanStep:
        step_id = str(uuid.uuid4())
        step = PlanStep(step_id=step_id, description=description, depth=depth)
        if depth >= max_depth:
            return step
        subtask_descriptions = self._llm_decompose(description, feedback)
        for sub_desc in subtask_descriptions:
            child = self._decompose(sub_desc, depth=depth + 1, max_depth=max_depth, feedback=feedback)
            step.sub_steps.append(child)
        return step

    def _llm_decompose(self, description: str, feedback: str) -> list[str]:
        try:
            prompt = (
                "Break the following goal into 2-4 recursive sub-goals. Return a JSON list of strings.\n"
                f"Goal: {description}\nFeedback: {feedback}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "[]"
            data = json.loads(content)
            return [item for item in data if isinstance(item, str)][:4]
        except Exception as exc:
            logger.error("Recursive decomposition failed: %s", exc)
            return [f"{description} :: step {i+1}" for i in range(2)]

    def _find_step(self, root: PlanStep, step_id: str) -> PlanStep | None:
        if root.step_id == step_id:
            return root
        for child in root.sub_steps:
            found = self._find_step(child, step_id)
            if found:
                return found
        return None

    def _serialize_step(self, step: PlanStep) -> dict[str, Any]:
        return {
            "step_id": step.step_id,
            "description": step.description,
            "status": step.status,
            "depth": step.depth,
            "sub_steps": [self._serialize_step(s) for s in step.sub_steps],
        }
