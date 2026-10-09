from typing import Any, List, Optional, Dict, Set, Callable
from collections import defaultdict


class ThoughtNode:
    def __init__(self, thought_id: str, content: str, score: float = 0.0):
        self.id = thought_id
        self.content = content
        self.score = score
        self.parents: Set["ThoughtNode"] = set()
        self.children: Set["ThoughtNode"] = set()

    def __repr__(self):
        return f"ThoughtNode({self.id!r}, score={self.score:.2f})"


class GraphOfThoughts:
    def __init__(self):
        self.nodes: Dict[str, ThoughtNode] = {}

    def add_node(self, node: ThoughtNode) -> None:
        self.nodes[node.id] = node

    def _connect(self, parent: ThoughtNode, child: ThoughtNode) -> None:
        parent.children.add(child)
        child.parents.add(parent)

    def split(self, node_id: str, branches: List[Dict[str, Any]]) -> List[ThoughtNode]:
        parent = self.nodes[node_id]
        new_nodes = []
        for i, branch in enumerate(branches):
            new_id = f"{node_id}_split_{i}"
            child = ThoughtNode(
                thought_id=new_id,
                content=branch.get("content", ""),
                score=branch.get("score", 0.0),
            )
            self.add_node(child)
            self._connect(parent, child)
            new_nodes.append(child)
        return new_nodes

    def merge(self, parent_ids: List[str], merged_id: str, merge_fn: Callable) -> ThoughtNode:
        contents = [self.nodes[pid].content for pid in parent_ids]
        merged_content = merge_fn(contents)
        scores = [self.nodes[pid].score for pid in parent_ids]
        merged_score = sum(scores) / len(scores) if scores else 0.0

        merged_node = ThoughtNode(thought_id=merged_id, content=merged_content, score=merged_score)
        self.add_node(merged_node)
        for pid in parent_ids:
            self._connect(self.nodes[pid], merged_node)
        return merged_node

    def aggregate(self, node_ids: List[str], aggregate_fn: Callable) -> ThoughtNode:
        contents = [self.nodes[nid].content for nid in node_ids]
        agg_content = aggregate_fn(contents)
        agg_score = max(self.nodes[nid].score for nid in node_ids)
        agg_id = f"agg_{'_'.join(node_ids)}"
        agg_node = ThoughtNode(thought_id=agg_id, content=agg_content, score=agg_score)
        self.add_node(agg_node)
        for nid in node_ids:
            self._connect(self.nodes[nid], agg_node)
        return agg_node

    def topological_sort(self) -> List[ThoughtNode]:
        in_degree = defaultdict(int)
        for node in self.nodes.values():
            for child in node.children:
                in_degree[child.id] += 1

        queue = [n for n in self.nodes.values() if in_degree[n.id] == 0]
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for child in node.children:
                in_degree[child.id] -= 1
                if in_degree[child.id] == 0:
                    queue.append(child)
        return result

    def best_node(self) -> Optional[ThoughtNode]:
        if not self.nodes:
            return None
        return max(self.nodes.values(), key=lambda n: n.score)
