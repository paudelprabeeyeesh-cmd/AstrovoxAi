from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class Task:
    task_id: str
    name: str
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class TaskInventory:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._history: List[Dict[str, Any]] = []

    def register(self, task_id: str, name: str, metadata: Optional[Dict[str, Any]] = None, status: str = "pending") -> Task:
        if task_id in self._tasks:
            raise ValueError(f"Task {task_id} already registered")
        task = Task(task_id=task_id, name=name, metadata=metadata or {}, status=status)
        self._tasks[task_id] = task
        self._history.append({"action": "register", "task_id": task_id, "name": name})
        return task

    def update_status(self, task_id: str, status: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found")
        task = self._tasks[task_id]
        old_status = task.status
        task.status = status
        self._history.append({
            "action": "update_status",
            "task_id": task_id,
            "old": old_status,
            "new": status,
        })
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_summary(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        for task in self._tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        return {
            "total_tasks": len(self._tasks),
            "status_counts": status_counts,
            "history_entries": len(self._history),
        }

    def remove(self, task_id: str) -> None:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found")
        del self._tasks[task_id]
        self._history.append({"action": "remove", "task_id": task_id})
