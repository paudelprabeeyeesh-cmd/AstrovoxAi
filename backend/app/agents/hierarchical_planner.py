from typing import Any, Dict, List, Optional
import logging
import uuid

logger = logging.getLogger(__name__)


class HierarchicalPlanner:
    def __init__(self):
        self.goals: Dict[str, Dict[str, Any]] = {}
        self.plans: Dict[str, List[Dict[str, Any]]] = {}
        self.goal_hierarchy: Dict[str, List[str]] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def add_goal(self, goal_id: str, description: str, parent: Optional[str] = None, priority: int = 0) -> Dict[str, Any]:
        goal = {
            "goal_id": goal_id,
            "description": description,
            "parent": parent,
            "priority": priority,
            "status": "pending",
            "children": [],
        }
        self.goals[goal_id] = goal
        if parent and parent in self.goals:
            self.goals[parent]["children"].append(goal_id)
            self.goal_hierarchy.setdefault(parent, []).append(goal_id)
        logger.info("Added goal %s with priority %d", goal_id, priority)
        return goal

    def decompose(self, goal_id: str, description: str) -> List[Dict[str, Any]]:
        goal = self.goals.get(goal_id, {"goal_id": goal_id, "description": description})
        steps = [
            {"step": f"analyze_{goal_id}", "goal": goal_id, "type": "analysis", "depends_on": []},
            {"step": f"execute_{goal_id}", "goal": goal_id, "type": "execution", "depends_on": [f"analyze_{goal_id}"]},
            {"step": f"validate_{goal_id}", "goal": goal_id, "type": "validation", "depends_on": [f"execute_{goal_id}"]},
        ]
        for step in steps:
            step["status"] = "pending"
        self.plans[goal_id] = steps
        return steps

    def long_term_plan(self, objective: str, horizon: int = 10) -> List[Dict[str, Any]]:
        milestones = []
        for i in range(horizon):
            milestones.append({
                "milestone": i + 1,
                "objective": objective,
                "target": f"phase_{i+1}",
                "status": "planned",
                "dependencies": [f"phase_{i}"] if i > 0 else [],
            })
        self.plans[objective] = milestones
        return milestones

    def plan(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        steps = self.decompose(goal, goal)
        return {
            "goal": goal,
            "steps": steps,
            "context": context,
            "hierarchy": self.goal_hierarchy.get(goal, []),
        }

    def update_dependencies(self, goal_id: str, deps: List[str]) -> None:
        self.dependencies[goal_id] = deps

    def get_ready_steps(self, goal_id: str) -> List[Dict[str, Any]]:
        plan = self.plans.get(goal_id, [])
        completed = {s["step"] for s in plan if s.get("status") == "completed"}
        ready = []
        for step in plan:
            if step.get("status") != "pending":
                continue
            if all(dep in completed for dep in step.get("depends_on", [])):
                ready.append(step)
        return ready

    def mark_completed(self, goal_id: str, step_name: str) -> None:
        plan = self.plans.get(goal_id, [])
        for step in plan:
            if step["step"] == step_name:
                step["status"] = "completed"
                break
