import logging
from dataclasses import dataclass, field
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    description: str
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    task_description: str
    subtasks: list[SubTask] = field(default_factory=list)
    estimated_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class PlanningEngine:
    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client
        self._openai = None

    def _get_openai(self):
        if self._openai is None:
            import openai
            self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def create_plan(self, task_description: str, context: dict[str, Any] | None = None) -> Plan:
        subtasks = self.decompose_task(task_description)
        valid = self.validate_plan(Plan(task_description=task_description, subtasks=subtasks))
        if not valid:
            logger.warning(f"Plan validation failed for task: {task_description[:50]}...")
        return Plan(task_description=task_description, subtasks=subtasks, metadata={"context": context or {}})

    def decompose_task(self, task: str) -> list[SubTask]:
        prompt = (
            "Break the following task into ordered subtasks. Return as a JSON list of objects with keys: "
            "description (string), priority (int 1-5), dependencies (list of strings).\n"
            f"Task: {task}"
        )
        try:
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.choices[0].message.content or "[]"
            import json
            raw = json.loads(content)
            return [SubTask(**item) for item in raw if isinstance(item, dict)]
        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            return [SubTask(description=task, priority=1, dependencies=[])]

    def validate_plan(self, plan: Plan) -> bool:
        if not plan.subtasks:
            return False
        priorities = [st.priority for st in plan.subtasks]
        if any(p < 1 or p > 5 for p in priorities):
            return False
        return True

    def execute_plan(self, plan: Plan) -> dict[str, Any]:
        results = []
        for subtask in plan.subtasks:
            prompt = (
                "Execute the following subtask and return a concise result summary.\n"
                f"Subtask: {subtask.description}"
            )
            try:
                client = self._get_openai()
                response = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                output = response.choices[0].message.content or ""
                results.append({"subtask": subtask.description, "output": output})
            except Exception as e:
                logger.error(f"Subtask execution failed: {e}")
                results.append({"subtask": subtask.description, "output": "", "error": str(e)})
        return {"success": True, "results": results, "metadata": plan.metadata}
