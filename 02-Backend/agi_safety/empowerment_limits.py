import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class CapabilityBudget:
    compute_units: float
    memory_mb: float
    api_calls: int
    time_seconds: float
    used_compute: float = 0.0
    used_memory: float = 0.0
    used_api_calls: int = 0
    used_time: float = 0.0

    def remaining_compute(self) -> float:
        return max(0.0, self.compute_units - self.used_compute)

    def remaining_api_calls(self) -> int:
        return max(0, self.api_calls - self.used_api_calls)

    def consume(self, compute: float = 0.0, memory: float = 0.0, api_calls: int = 0, time_s: float = 0.0) -> bool:
        if self.remaining_compute() < compute:
            return False
        if self.used_memory + memory > self.memory_mb:
            return False
        if self.used_api_calls + api_calls > self.api_calls:
            return False
        self.used_compute += compute
        self.used_memory += memory
        self.used_api_calls += api_calls
        self.used_time += time_s
        return True


@dataclass
class ContainmentResult:
    contained: bool
    reason: str
    risk_score: float


class CapabilityController:
    def __init__(self, budget: CapabilityBudget):
        self.budget = budget
        self._tool_registry: Dict[str, Callable] = {}
        self._sandbox_depth: int = 1

    def register_tool(self, name: str, fn: Callable, risk_level: str = "low") -> None:
        self._tool_registry[name] = fn

    def execute_within_budget(self, name: str, compute_cost: float, **kwargs) -> Dict:
        if name not in self._tool_registry:
            return {"success": False, "error": "tool_not_found"}
        if not self.budget.consume(compute=compute_cost):
            return {"success": False, "error": "budget_exhausted"}
        try:
            result = self._tool_registry[name](**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def increase_sandbox_depth(self) -> None:
        self._sandbox_depth = min(self._sandbox_depth + 1, 5)

    def get_remaining_budget(self) -> Dict:
        return {
            "compute_units": round(self.budget.remaining_compute(), 4),
            "api_calls": self.budget.remaining_api_calls(),
            "memory_mb": round(self.budget.memory_mb - self.budget.used_memory, 4),
            "sandbox_depth": self._sandbox_depth,
        }


class IsolationBox:
    def __init__(self, barrier_fn: Callable, risk_threshold: float = 0.3):
        self.barrier_fn = barrier_fn
        self.risk_threshold = risk_threshold
        self.traffic_log: List[Dict] = []

    def attempt_egress(self, payload: Any) -> ContainmentResult:
        risk = self._assess_risk(payload)
        allowed = risk < self.risk_threshold
        self.traffic_log.append({"payload": str(payload)[:100], "risk": round(risk, 4), "allowed": allowed})
        return ContainmentResult(
            contained=not allowed,
            reason="blocked_by_box" if not allowed else "allowed",
            risk_score=round(risk, 4),
        )

    def _assess_risk(self, payload: Any) -> float:
        s = str(payload)
        if any(word in s.lower() for word in ["escape", "exfiltrate", "self_replicate"]):
            return 0.9
        return 0.1

    def get_traffic_summary(self) -> Dict:
        if not self.traffic_log:
            return {"total": 0, "blocked": 0, "allowed": 0}
        blocked = sum(1 for t in self.traffic_log if not t["allowed"])
        return {
            "total": len(self.traffic_log),
            "blocked": blocked,
            "allowed": len(self.traffic_log) - blocked,
        }
