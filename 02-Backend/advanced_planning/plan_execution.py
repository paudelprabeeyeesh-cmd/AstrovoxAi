
from typing import Any, Callable, Dict, List, Optional


class ExecutionMonitor:
    def __init__(self, plan: List[Any], apply_fn: Callable[[Dict[str, Any], Any], Dict[str, Any]],
                 goal_fn: Callable[[Dict[str, Any]], bool]):
        self.plan = list(plan)
        self.apply_fn = apply_fn
        self.goal_fn = goal_fn
        self.current_index = 0
        self.execution_log: List[Dict[str, Any]] = []
        self.contingencies_triggered: List[Dict[str, Any]] = []

    def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(initial_state)
        self.execution_log.append({"step": 0, "state": dict(state), "action": None, "status": "start"})
        for i, action in enumerate(self.plan):
            try:
                state = self.apply_fn(state, action)
                self.execution_log.append({"step": i + 1, "state": dict(state), "action": action, "status": "success"})
                self.current_index = i + 1
            except Exception as e:
                self.execution_log.append({"step": i + 1, "state": dict(state), "action": action,
                                           "status": "error", "error": str(e)})
                self.contingencies_triggered.append({"step": i + 1, "error": str(e), "state": dict(state)})
                break
            if self.goal_fn(state):
                self.execution_log.append({"step": i + 1, "state": dict(state), "status": "goal_reached"})
                self.current_index = i + 1
                break
        return {"final_state": state, "goal_reached": self.goal_fn(state), "execution_log": self.execution_log,
                "contingencies": self.contingencies_triggered, "completed_steps": self.current_index}

    def has_contingency(self) -> bool:
        return len(self.contingencies_triggered) > 0

    def get_progress(self) -> float:
        return self.current_index / len(self.plan) if self.plan else 0.0


class ContingencyHandler:
    def __init__(self, recovery_plans: Optional[Dict[str, List[Any]]] = None):
        self.recovery_plans = recovery_plans or {}
        self.executed_recoveries: List[Dict[str, Any]] = []

    def handle_error(self, error_type: str, current_state: Dict[str, Any]) -> Optional[List[Any]]:
        recovery = self.recovery_plans.get(error_type)
        if recovery:
            self.executed_recoveries.append({"error_type": error_type, "recovery_plan": recovery})
            return recovery
        return None

    def execute_recovery(self, recovery_plan: List[Any], apply_fn: Callable[[Dict[str, Any], Any], Dict[str, Any]],
                         state: Dict[str, Any]) -> Dict[str, Any]:
        current = dict(state)
        log = []
        for action in recovery_plan:
            try:
                current = apply_fn(current, action)
                log.append({"action": action, "status": "success", "state": dict(current)})
            except Exception as e:
                log.append({"action": action, "status": "error", "error": str(e)})
                break
        return {"state": current, "log": log, "success": len([l for l in log if l["status"] == "success"]) == len(
            recovery_plan)}
