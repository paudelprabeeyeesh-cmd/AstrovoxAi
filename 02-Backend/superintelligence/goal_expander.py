from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import copy


@dataclass
class GoalNode:
    id: str
    description: str
    priority: float
    depth: int
    children: List["GoalNode"] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    estimated_effort: float = 1.0


class GoalExpander:
    def __init__(self, max_depth: int = 5, branching_factor: int = 3):
        self.max_depth = int(max_depth)
        self.branching_factor = int(branching_factor)
        self.expansion_log: List[Dict[str, Any]] = []
        self.node_counter = 0

    def expand(self, goal_description: str, priority: float = 1.0, constraints: Optional[List[str]] = None) -> GoalNode:
        self.node_counter = 0
        self.expansion_log = []
        root = GoalNode(
            id=self._next_id(),
            description=goal_description,
            priority=float(priority),
            depth=0,
            constraints=list(constraints or []),
        )
        self._expand_recursive(root)
        return root

    def _next_id(self) -> str:
        self.node_counter += 1
        return f"goal_{self.node_counter}"

    def _expand_recursive(self, node: GoalNode) -> None:
        if node.depth >= self.max_depth:
            return
        sub_descriptions = self._decompose(node.description, node.depth)
        for desc in sub_descriptions:
            child = GoalNode(
                id=self._next_id(),
                description=desc,
                priority=max(0.1, node.priority * 0.8),
                depth=node.depth + 1,
                constraints=list(node.constraints),
                estimated_effort=max(0.1, node.estimated_effort * 0.6),
            )
            node.children.append(child)
            self.expansion_log.append({
                "parent_id": node.id,
                "child_id": child.id,
                "depth": child.depth,
                "description": child.description,
            })
            self._expand_recursive(child)

    def _decompose(self, description: str, depth: int) -> List[str]:
        words = description.split()
        if len(words) <= 2:
            return [f"{description} part {i+1}" for i in range(self.branching_factor)]
        templates = [
            f"Analyze {description}",
            f"Implement {description}",
            f"Validate {description}",
        ]
        return templates[: self.branching_factor]

    def get_goal_tree(self, root: GoalNode) -> Dict[str, Any]:
        return self._serialize_node(root)

    def _serialize_node(self, node: GoalNode) -> Dict[str, Any]:
        return {
            "id": node.id,
            "description": node.description,
            "priority": node.priority,
            "depth": node.depth,
            "estimated_effort": node.estimated_effort,
            "children": [self._serialize_node(child) for child in node.children],
        }

    def get_total_goals(self, root: GoalNode) -> int:
        count = 1
        for child in root.children:
            count += self.get_total_goals(child)
        return count

    def get_leaf_goals(self, root: GoalNode) -> List[GoalNode]:
        if not root.children:
            return [root]
        leaves = []
        for child in root.children:
            leaves.extend(self.get_leaf_goals(child))
        return leaves

    def prioritize_goals(self, root: GoalNode) -> List[GoalNode]:
        all_nodes = self._collect_nodes(root)
        return sorted(all_nodes, key=lambda n: n.priority, reverse=True)

    def _collect_nodes(self, node: GoalNode) -> List[GoalNode]:
        nodes = [node]
        for child in node.children:
            nodes.extend(self._collect_nodes(child))
        return nodes

    def get_expansion_stats(self) -> Dict[str, Any]:
        return {
            "total_expansions": len(self.expansion_log),
            "max_depth": self.max_depth,
            "branching_factor": self.branching_factor,
        }
