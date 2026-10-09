import numpy as np
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
import time


@dataclass
class TaskSet:
    name: str
    rules: Dict[str, Any]
    priority: float
    active: bool = True
    switch_cost: float = 0.2
    created_at: float = field(default_factory=time.time)

    def get_utility(self, current_time: float) -> float:
        age = current_time - self.created_at
        return self.priority * np.exp(-0.01 * age)


class TaskSwitchingCost:
    def __init__(self, base_cost: float = 0.2, interference_decay: float = 0.5):
        self.base_cost = base_cost
        self.interference_decay = interference_decay
        self._switch_history: List[Dict[str, Any]] = []

    def compute_switch_cost(self, from_task: TaskSet, to_task: TaskSet) -> float:
        similarity = self._rule_similarity(from_task.rules, to_task.rules)
        interference = 1.0 - similarity
        cost = self.base_cost + interference * (1.0 - self.interference_decay)
        self._switch_history.append({
            "from": from_task.name,
            "to": to_task.name,
            "cost": cost,
            "timestamp": time.time(),
        })
        return min(cost, 1.0)

    def _rule_similarity(self, rules_a: Dict[str, Any], rules_b: Dict[str, Any]) -> float:
        common_keys = set(rules_a.keys()) & set(rules_b.keys())
        if not common_keys:
            return 0.0
        matches = sum(1 for k in common_keys if rules_a[k] == rules_b[k])
        return matches / len(common_keys)


class InhibitoryControl:
    def __init__(self, inhibition_strength: float = 0.5, recovery_rate: float = 0.1):
        self.inhibition_strength = inhibition_strength
        self.recovery_rate = recovery_rate
        self._inhibited_items: Dict[str, float] = {}

    def inhibit(self, item_id: str) -> None:
        self._inhibited_items[item_id] = self.inhibition_strength

    def release(self, item_id: str) -> None:
        if item_id in self._inhibited_items:
            del self._inhibited_items[item_id]

    def get_suppression(self, item_id: str) -> float:
        if item_id not in self._inhibited_items:
            return 0.0
        self._inhibited_items[item_id] *= np.exp(-self.recovery_rate)
        if self._inhibited_items[item_id] < 0.01:
            del self._inhibited_items[item_id]
            return 0.0
        return self._inhibited_items[item_id]

    def step(self, dt: float = 1.0) -> None:
        expired = []
        for item_id, level in self._inhibited_items.items():
            new_level = level * np.exp(-self.recovery_rate * dt)
            if new_level < 0.01:
                expired.append(item_id)
            else:
                self._inhibited_items[item_id] = new_level
        for item_id in expired:
            del self._inhibited_items[item_id]


class ExecutiveControlSystem:
    def __init__(self, max_active_tasks: int = 4):
        self.max_active_tasks = max_active_tasks
        self.task_sets: Dict[str, TaskSet] = {}
        self.active_task: Optional[str] = None
        self.switching_cost_model = TaskSwitchingCost()
        self.inhibitory_control = InhibitoryControl()
        self._goal_stack: List[str] = []
        self._performance_log: List[Dict[str, Any]] = []

    def add_task(self, task: TaskSet) -> bool:
        if len(self.task_sets) >= self.max_active_tasks and task.name not in self.task_sets:
            lowest = min(self.task_sets.values(), key=lambda t: t.get_utility(time.time()))
            if task.priority > lowest.priority:
                del self.task_sets[lowest.name]
            else:
                return False
        self.task_sets[task.name] = task
        return True

    def switch_task(self, new_task_name: str) -> float:
        if new_task_name not in self.task_sets:
            raise ValueError(f"Task {new_task_name} not found")
        if self.active_task is not None:
            from_task = self.task_sets[self.active_task]
            to_task = self.task_sets[new_task_name]
            cost = self.switching_cost_model.compute_switch_cost(from_task, to_task)
            self.inhibitory_control.inhibit(self.active_task)
            self.active_task = new_task_name
            self._performance_log.append({
                "action": "switch",
                "from": from_task.name,
                "to": new_task_name,
                "cost": cost,
                "timestamp": time.time(),
            })
            return cost
        self.active_task = new_task_name
        return 0.0

    def set_goal(self, goal: str) -> None:
        self._goal_stack.append(goal)
        if goal in self.task_sets:
            self.switch_task(goal)

    def pop_goal(self) -> Optional[str]:
        if self._goal_stack:
            return self._goal_stack.pop()
        return None

    def execute_action(self, action: Callable, action_context: str) -> Any:
        if self.active_task is None:
            raise RuntimeError("No active task set")
        suppression = self.inhibitory_control.get_suppression(action_context)
        if suppression > 0.8:
            return None
        result = action()
        self._performance_log.append({
            "action": "execute",
            "context": action_context,
            "suppression": suppression,
            "timestamp": time.time(),
        })
        return result

    def get_performance_metrics(self) -> Dict[str, Any]:
        if not self._performance_log:
            return {"total_actions": 0}
        costs = [entry["cost"] for entry in self._performance_log if entry["action"] == "switch"]
        return {
            "total_actions": len(self._performance_log),
            "avg_switch_cost": float(np.mean(costs)) if costs else 0.0,
            "active_task": self.active_task,
        }
