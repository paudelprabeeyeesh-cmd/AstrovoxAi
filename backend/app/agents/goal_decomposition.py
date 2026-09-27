from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class GoalDecomposition:
    def __init__(self):
        self.decompositions: Dict[str, List[Dict[str, Any]]] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.parallel_groups: Dict[str, List[List[str]]] = {}

    def decompose(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        steps = [
            {"step": f"analyze_{goal}", "goal": goal, "type": "analysis", "depends_on": [], "parallel_group": 0},
            {"step": f"execute_{goal}", "goal": goal, "type": "execution", "depends_on": [f"analyze_{goal}"], "parallel_group": 1},
            {"step": f"validate_{goal}", "goal": goal, "type": "validation", "depends_on": [f"execute_{goal}"], "parallel_group": 2},
        ]
        self.decompositions[goal] = steps
        self.dependency_graph[goal] = [f"analyze_{goal}", f"execute_{goal}", f"validate_{goal}"]
        self.parallel_groups[goal] = [
            [f"analyze_{goal}"],
            [f"execute_{goal}"],
            [f"validate_{goal}"],
        ]
        return steps

    def get_decomposition(self, goal: str) -> List[Dict[str, Any]]:
        return self.decompositions.get(goal, [])

    def merge(self, goal_a: str, goal_b: str) -> List[Dict[str, Any]]:
        decomp_a = self.decompositions.get(goal_a, [])
        decomp_b = self.decompositions.get(goal_b, [])
        bridge = {"step": f"bridge_{goal_a}_{goal_b}", "goal": goal_a, "type": "bridge", "depends_on": [], "parallel_group": -1}
        merged = decomp_a + [bridge] + decomp_b
        self.decompositions[f"{goal_a}__{goal_b}"] = merged
        return merged

    def get_parallel_steps(self, goal: str) -> List[List[Dict[str, Any]]]:
        groups = self.parallel_groups.get(goal, [])
        result = []
        for group in groups:
            result.append([step for step in self.decompositions.get(goal, []) if step.get("parallel_group") == groups.index(group)])
        return result

    def resolve_dependencies(self, goal: str) -> List[str]:
        graph = self.dependency_graph.get(goal, [])
        visited = set()
        order = []
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for step in self.decompositions.get(goal, []):
                if step["step"] == node:
                    for dep in step.get("depends_on", []):
                        visit(dep)
            order.append(node)
        for node in graph:
            visit(node)
        return order

    def add_step(self, goal: str, step: Dict[str, Any]) -> None:
        self.decompositions.setdefault(goal, []).append(step)
        self.dependency_graph.setdefault(goal, []).append(step.get("step", ""))
