import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.planning import PlanningEngine, SubTask

logger = logging.getLogger(__name__)


@dataclass
class TaskNode:
    task: str
    depth: int = 0
    children: list["TaskNode"] = field(default_factory=list)
    complexity: float = 0.0
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    goal_id: str
    description: str
    success_criteria: list[str] = field(default_factory=list)
    decomposition: TaskNode | None = None
    progress: float = 0.0
    status: str = "pending"
    created_at: float = field(default_factory=time.time)


class TaskDecomposer:
    def __init__(self, llm_client: Any | None = None) -> None:
        self.engine = PlanningEngine(llm_client)
        self._goals: dict[str, Goal] = {}

    def decompose(self, task: str, max_depth: int = 3) -> TaskNode:
        root = TaskNode(task=task, depth=0, complexity=self.estimate_complexity(task))
        if max_depth <= 1:
            return root
        subtasks = self.engine.decompose_task(task)
        for st in subtasks:
            child = TaskNode(task=st.description, depth=1, complexity=self.estimate_complexity(st.description))
            if max_depth > 2:
                child.children = [
                    TaskNode(task=f"{st.description} :: step {i+1}", depth=2, complexity=self.estimate_complexity(st.description) * 0.3)
                    for i in range(max(1, int(st.priority)))
                ]
            root.children.append(child)
        return root

    def estimate_complexity(self, task: str) -> float:
        heuristic = min(len(task.split()) / 50.0, 1.0)
        try:
            prompt = (
                "Estimate task complexity as a float between 0.0 and 1.0. Return only the number.\n"
                f"Task: {task}"
            )
            import importlib
            openai_mod = importlib.import_module("openai")
            from ...config import settings
            client = openai_mod.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            value = float((response.choices[0].message.content or "0.5").strip())
            return max(0.0, min(1.0, value))
        except Exception as e:
            logger.error(f"Complexity estimation failed: {e}")
            return round(heuristic, 2)

    def identify_dependencies(self, tasks: list[SubTask]) -> dict[str, list[str]]:
        dep_map: dict[str, list[str]] = {}
        for t in tasks:
            dep_map[t.description] = list(t.dependencies)
        return dep_map

    def optimize_execution_order(self, tasks: list[SubTask]) -> list[str]:
        dep_map = self.identify_dependencies(tasks)
        visited = set()
        order: list[str] = []

        def visit(desc: str) -> None:
            if desc in visited:
                return
            visited.add(desc)
            for dep in dep_map.get(desc, []):
                visit(dep)
            order.append(desc)

        for t in tasks:
            visit(t.description)
        return order

    def decompose_goal(self, goal_description: str, max_depth: int = 3) -> Goal:
        goal_id = str(uuid.uuid4())
        root = self.decompose(goal_description, max_depth=max_depth)
        goal = Goal(
            goal_id=goal_id,
            description=goal_description,
            success_criteria=[],
            decomposition=root,
            status="decomposed",
        )
        self._goals[goal_id] = goal
        logger.info("Decomposed goal %s into %d subtasks", goal_id, len(root.children))
        return goal

    def track_goal(self, goal_id: str, progress: float, status: str | None = None) -> dict[str, Any]:
        goal = self._goals.get(goal_id)
        if not goal:
            return {"goal_id": goal_id, "status": "not_found"}
        goal.progress = max(0.0, min(1.0, progress))
        if status:
            goal.status = status
        logger.info("Goal %s progress updated to %.2f", goal_id, goal.progress)
        return {"goal_id": goal_id, "progress": goal.progress, "status": goal.status}

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        return {
            "goal_id": goal.goal_id,
            "description": goal.description,
            "success_criteria": goal.success_criteria,
            "progress": goal.progress,
            "status": goal.status,
            "created_at": goal.created_at,
        }

    def list_goals(self, status: str | None = None) -> list[str]:
        goals = list(self._goals.values())
        if status:
            goals = [g for g in goals if g.status == status]
        return [g.goal_id for g in goals]

    def get_subtask_tree(self, goal_id: str) -> dict[str, Any] | None:
        goal = self._goals.get(goal_id)
        if not goal or not goal.decomposition:
            return None
        return self._serialize_node(goal.decomposition)

    def _serialize_node(self, node: TaskNode) -> dict[str, Any]:
        return {
            "task": node.task,
            "depth": node.depth,
            "complexity": node.complexity,
            "status": node.status,
            "children": [self._serialize_node(child) for child in node.children],
        }
