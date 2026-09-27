from typing import Any, Dict, List, Optional
import logging
import random

logger = logging.getLogger(__name__)


class LongTermPlanner:
    def __init__(self, horizon: int = 10):
        self.horizon = horizon
        self.plans: Dict[str, List[Dict[str, Any]]] = {}
        self.scenarios: Dict[str, List[Dict[str, Any]]] = {}
        self.resource_forecasts: Dict[str, Dict[str, Any]] = {}

    def plan(self, objective: str, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        milestones = []
        for i in range(self.horizon):
            milestone = {
                "milestone": i + 1,
                "objective": objective,
                "target": f"phase_{i+1}",
                "constraints": constraints,
                "status": "planned",
                "progress": 0.0,
                "risk": self._estimate_risk(i, self.horizon),
                "contingency": self._generate_contingency(i),
            }
            milestones.append(milestone)
        self.plans[objective] = milestones
        return milestones

    def _estimate_risk(self, phase: int, total: int) -> str:
        if phase < total * 0.3:
            return "low"
        if phase < total * 0.7:
            return "medium"
        return "high"

    def _generate_contingency(self, phase: int) -> Dict[str, Any]:
        return {
            "fallback": f"fallback_phase_{phase+1}",
            "buffer": random.uniform(0.1, 0.3),
            "trigger_condition": f"progress < 0.5 at phase {phase}",
        }

    def update_progress(self, objective: str, milestone_index: int, status: str, progress: float = 0.0) -> Dict[str, Any]:
        plan = self.plans.get(objective, [])
        if 0 <= milestone_index < len(plan):
            plan[milestone_index]["status"] = status
            plan[milestone_index]["progress"] = max(0.0, min(1.0, progress))
            return plan[milestone_index]
        return {"error": "invalid milestone"}

    def get_plan(self, objective: str) -> List[Dict[str, Any]]:
        return self.plans.get(objective, [])

    def generate_scenario(self, objective: str, name: str, variation: Dict[str, Any]) -> List[Dict[str, Any]]:
        base = self.plans.get(objective, [])
        scenario = []
        for milestone in base:
            m = dict(milestone)
            m["target"] = f"{name}_{m['target']}"
            m["constraints"] = {**m.get("constraints", {}), **variation}
            scenario.append(m)
        self.scenarios[name] = scenario
        return scenario

    def predict_completion(self, objective: str) -> Dict[str, Any]:
        plan = self.plans.get(objective, [])
        if not plan:
            return {"error": "no plan"}
        completed = sum(1 for m in plan if m.get("status") == "completed")
        in_progress = sum(1 for m in plan if m.get("status") == "in_progress")
        progress = completed / len(plan)
        return {
            "objective": objective,
            "total_milestones": len(plan),
            "completed": completed,
            "in_progress": in_progress,
            "progress": progress,
            "eta_phases": len(plan) - completed - in_progress,
        }

    def add_resource_forecast(self, objective: str, forecast: Dict[str, Any]) -> None:
        self.resource_forecasts[objective] = forecast

    def adapt_horizon(self, objective: str, new_horizon: int) -> List[Dict[str, Any]]:
        current = self.plans.get(objective, [])
        if new_horizon > len(current):
            for i in range(len(current), new_horizon):
                current.append({
                    "milestone": i + 1,
                    "objective": objective,
                    "target": f"phase_{i+1}",
                    "status": "planned",
                    "progress": 0.0,
                    "risk": "medium",
                    "contingency": {},
                })
        elif new_horizon < len(current):
            current = current[:new_horizon]
        self.plans[objective] = current
        self.horizon = max(self.horizon, new_horizon)
        return current
