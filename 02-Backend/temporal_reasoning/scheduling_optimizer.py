from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Task:
    task_id: str
    duration: float
    resources: Dict[str, int] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: float = 0.0


@dataclass
class ScheduledTask:
    task_id: str
    start: float
    end: float
    resources: Dict[str, int] = field(default_factory=dict)


class SchedulingOptimizer:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.resource_capacities: Dict[str, int] = {}
        self.schedule: List[ScheduledTask] = []

    def add_task(self, task_id: str, duration: float, resources: Optional[Dict[str, int]] = None, dependencies: Optional[List[str]] = None, priority: float = 0.0) -> None:
        self.tasks[task_id] = Task(
            task_id=task_id,
            duration=duration,
            resources=resources or {},
            dependencies=dependencies or [],
            priority=priority,
        )

    def set_capacity(self, resource: str, capacity: int) -> None:
        self.resource_capacities[resource] = capacity

    def optimize(self) -> List[ScheduledTask]:
        task_map = {tid: t for tid, t in self.tasks.items()}
        earliest_start: Dict[str, float] = {}
        sorted_tasks = self._topological_sort()
        for tid in sorted_tasks:
            task = task_map[tid]
            est = 0.0
            for dep in task.dependencies:
                est = max(est, earliest_start.get(dep, 0.0) + task_map[dep].duration)
            earliest_start[tid] = est
        schedule = []
        for tid in sorted_tasks:
            task = task_map[tid]
            schedule.append(ScheduledTask(task_id=tid, start=earliest_start[tid], end=earliest_start[tid] + task.duration, resources=dict(task.resources)))
        self.schedule = schedule
        return schedule

    def makespan(self) -> float:
        if not self.schedule:
            return 0.0
        return max(s.end for s in self.schedule)

    def resource_usage_at(self, time: float) -> Dict[str, int]:
        usage: Dict[str, int] = {}
        for s in self.schedule:
            if s.start <= time < s.end:
                for res, amt in s.resources.items():
                    usage[res] = usage.get(res, 0) + amt
        return usage

    def _topological_sort(self) -> List[str]:
        in_degree = {tid: len(self.tasks[tid].dependencies) for tid in self.tasks}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []
        adj = {tid: [] for tid in self.tasks}
        for tid, task in self.tasks.items():
            for dep in task.dependencies:
                if dep in adj:
                    adj[dep].append(tid)
        while queue:
            node = queue.pop(0)
            result.append(node)
            for succ in adj.get(node, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)
        return result
