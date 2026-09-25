import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    description: str
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    plan_id: str
    task_description: str
    subtasks: list[SubTask] = field(default_factory=list)
    estimated_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class PlanningEngine:
    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm = llm_client
        self._openai = None
        self._plans: dict[str, Plan] = {}

    def _get_openai(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def create_plan(self, task_description: str, context: dict[str, Any] | None = None) -> Plan:
        plan_id = str(uuid.uuid4())
        subtasks = self.decompose_task(task_description)
        valid = self.validate_plan(Plan(plan_id=plan_id, task_description=task_description, subtasks=subtasks))
        if not valid:
            logger.warning("Plan validation failed for task: %s...", task_description[:50])
        plan = Plan(plan_id=plan_id, task_description=task_description, subtasks=subtasks, metadata={"context": context or {}})
        self._plans[plan_id] = plan
        logger.info("Created plan %s with %d subtasks", plan_id, len(subtasks))
        return plan

    def decompose_task(self, task: str) -> list[SubTask]:
        prompt = (
            "Break the following task into ordered, actionable subtasks. Return as a JSON list of objects with keys: "
            "description (string), priority (int 1-5), dependencies (list of strings), estimated_duration (float hours).\n"
            f"Task: {task}"
        )
        try:
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "[]"
            raw = json.loads(content)
            return [SubTask(**item) for item in raw if isinstance(item, dict)]
        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            return [SubTask(description=task, priority=1, dependencies=[], estimated_duration=1.0)]

    def validate_plan(self, plan: Plan) -> bool:
        if not plan.subtasks:
            return False
        priorities = [st.priority for st in plan.subtasks]
        if any(p < 1 or p > 5 for p in priorities):
            return False
        return True

    def execute_plan(self, plan: Plan) -> dict[str, Any]:
        results = []
        order = self._topological_sort(plan.subtasks)
        for desc in order:
            subtask = next((s for s in plan.subtasks if s.description == desc), None)
            if not subtask:
                continue
            prompt = (
                "Execute the following subtask and return a concise result summary.\n"
                f"Subtask: {subtask.description}\nPriority: {subtask.priority}\nEstimated duration: {subtask.estimated_duration}h"
            )
            try:
                client = self._get_openai()
                response = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                output = response.choices[0].message.content or ""
                results.append({"subtask": subtask.description, "output": output, "status": "completed"})
            except Exception as e:
                logger.error(f"Subtask execution failed: {e}")
                results.append({"subtask": subtask.description, "output": "", "error": str(e), "status": "failed"})
        return {"success": True, "results": results, "metadata": plan.metadata}

    def refine_plan(self, plan_id: str, feedback: str) -> dict[str, Any]:
        plan = self._plans.get(plan_id)
        if not plan:
            return {"plan_id": plan_id, "status": "not_found"}

        try:
            prompt = (
                "Refine the plan based on feedback. Return JSON with keys: refined (bool), added_subtasks (list of SubTask-like objects), removed_subtasks (list of strings).\n"
                f"Current plan: {plan.task_description}\nSubtasks: {[s.description for s in plan.subtasks]}\nFeedback: {feedback}"
            )
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            added = [SubTask(**item) for item in data.get("added_subtasks", []) if isinstance(item, dict)]
            removed = set(data.get("removed_subtasks", []))
            plan.subtasks = [s for s in plan.subtasks if s.description not in removed] + added
            logger.info("Refined plan %s: added=%d, removed=%d", plan_id, len(added), len(removed))
            return {"plan_id": plan_id, "status": "refined", "added": len(added), "removed": len(removed)}
        except Exception as exc:
            logger.error("Plan refinement failed: %s", exc)
            return {"plan_id": plan_id, "status": "error", "error": str(exc)}

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        return {
            "plan_id": plan.plan_id,
            "task_description": plan.task_description,
            "subtasks": [{"description": s.description, "priority": s.priority, "dependencies": s.dependencies} for s in plan.subtasks],
            "estimated_tokens": plan.estimated_tokens,
            "metadata": plan.metadata,
            "created_at": plan.created_at,
        }

    def list_plans(self) -> list[str]:
        return list(self._plans.keys())

    def _topological_sort(self, subtasks: list[SubTask]) -> list[str]:
        dep_map: dict[str, list[str]] = {s.description: list(s.dependencies) for s in subtasks}
        visited: set[str] = set()
        order: list[str] = []

        def visit(desc: str) -> None:
            if desc in visited:
                return
            visited.add(desc)
            for dep in dep_map.get(desc, []):
                visit(dep)
            order.append(desc)

        for s in subtasks:
            visit(s.description)
        return order
