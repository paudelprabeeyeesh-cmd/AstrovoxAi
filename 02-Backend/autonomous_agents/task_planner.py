from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class Task:
    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None


class TaskPlanner:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._counter = 0

    def add_task(self, description: str, dependencies: Optional[List[str]] = None) -> Task:
        self._counter += 1
        task = Task(id=f"task_{self._counter}", description=description, dependencies=dependencies or [])
        self.tasks[task.id] = task
        return task

    def plan(self, goal: str) -> List[Task]:
        ordered: List[Task] = []
        visited: Set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            visited.add(task_id)
            task = self.tasks.get(task_id)
            if task is None:
                return
            for dep in task.dependencies:
                visit(dep)
            ordered.append(task)

        for task_id in list(self.tasks.keys()):
            visit(task_id)
        return ordered

    def mark_complete(self, task_id: str, result: Any = None) -> Optional[Task]:
        task = self.tasks.get(task_id)
        if task is None:
            return None
        task.status = "completed"
        task.result = result
        return task

    def get_failed_dependencies(self, task_id: str) -> List[str]:
        task = self.tasks.get(task_id)
        if task is None:
            return []
        return [dep for dep in task.dependencies if self.tasks.get(dep, Task(id=dep, description="")).status == "failed"]
