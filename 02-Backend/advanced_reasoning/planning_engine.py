from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Task:
    id: str
    description: str
    complexity: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    estimated_tokens: int = 100
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Plan:
    tasks: List[Task]
    layers: List[List[str]]
    total_complexity: float = 0.0


class PlanningEngine:
    def __init__(self, max_layer_size: int = 8):
        self.max_layer_size = max_layer_size

    def decompose(self, task: Task) -> Plan:
        tasks = self._expand_task(task)
        layers = self._resolve_layers(tasks)
        total_complexity = sum(t.complexity for t in tasks)
        return Plan(tasks=tasks, layers=layers, total_complexity=total_complexity)

    def _expand_task(self, task: Task) -> List[Task]:
        if not task.dependencies:
            return [task]
        expanded = []
        for dep_id in task.dependencies:
            expanded.append(Task(id=dep_id, description=f"Subtask {dep_id}", complexity=task.complexity * 0.4))
        expanded.append(task)
        return expanded

    def _resolve_layers(self, tasks: List[Task]) -> List[List[str]]:
        task_map = {t.id: t for t in tasks}
        remaining = set(task_map.keys())
        layers = []
        visited = set()
        while remaining:
            layer = []
            for task_id in sorted(remaining):
                task = task_map[task_id]
                if all(dep in visited for dep in task.dependencies):
                    layer.append(task_id)
            if not layer:
                raise ValueError("Circular dependency detected")
            if len(layer) > self.max_layer_size:
                for i in range(0, len(layer), self.max_layer_size):
                    layers.append(layer[i:i + self.max_layer_size])
            else:
                layers.append(layer)
            visited.update(layer)
            remaining -= set(layer)
        return layers

    def estimate_execution_time(self, plan: Plan) -> Dict[str, float]:
        task_map = {t.id: t for t in plan.tasks}
        layer_durations = []
        for layer in plan.layers:
            flat = [item for sub in layer for item in (sub if isinstance(sub[0], list) else [sub])] if layer and isinstance(layer[0], list) else layer
            durations = [task_map[t].estimated_tokens / 1000.0 for t in flat if t in task_map]
            layer_durations.append(max(durations) if durations else 0.0)
        return {"total_layers": len(layer_durations), "estimated_seconds": sum(layer_durations)}
