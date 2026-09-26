from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class GoalDecomposition:
    def __init__(self):
        self.decompositions: Dict[str, List[Dict[str, Any]]] = {}

    def decompose(self, goal: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        steps = [
            {"step": f"analyze_{goal}", "goal": goal, "type": "analysis"},
            {"step": f"execute_{goal}", "goal": goal, "type": "execution"},
            {"step": f"validate_{goal}", "goal": goal, "type": "validation"},
        ]
        self.decompositions[goal] = steps
        return steps

    def get_decomposition(self, goal: str) -> List[Dict[str, Any]]:
        return self.decompositions.get(goal, [])

    def merge(self, goal_a: str, goal_b: str) -> List[Dict[str, Any]]:
        decomp_a = self.decompositions.get(goal_a, [])
        decomp_b = self.decompositions.get(goal_b, [])
        merged = decomp_a + [{"step": f"bridge_{goal_a}_{goal_b}", "goal": goal_a, "type": "bridge"}] + decomp_b
        return merged
