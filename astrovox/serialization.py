"""Graph serialization for the computation graph.

Provides JSON and protocol-buffer-like serialization for the dynamic
computation graph so models and training state can be saved and reloaded
without depending on pickle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class GraphNodeSpec:
    name: str
    op: str
    inputs: tuple[str, ...] = ()
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSpec:
    nodes: Dict[str, GraphNodeSpec] = field(default_factory=dict)
    outputs: tuple[str, ...] = ()

    def add_node(self, node: GraphNodeSpec) -> None:
        self.nodes[node.name] = node

    def to_json(self) -> str:
        payload = {
            "nodes": [
                {"name": node.name, "op": node.op, "inputs": list(node.inputs), "attrs": node.attrs}
                for node in self.nodes.values()
            ],
            "outputs": list(self.outputs),
        }
        return json.dumps(payload, indent=2)

    @classmethod
    def from_json(cls, data: str) -> GraphSpec:
        payload = json.loads(data)
        nodes = {
            item["name"]: GraphNodeSpec(
                name=item["name"], op=item["op"], inputs=tuple(item.get("inputs", [])), attrs=item.get("attrs", {})
            )
            for item in payload.get("nodes", [])
        }
        return cls(nodes=nodes, outputs=tuple(payload.get("outputs", [])))

    def reachable(self) -> set[str]:
        visited: set[str] = set()
        stack = list(self.outputs)
        while stack:
            name = stack.pop()
            if name in visited:
                continue
            visited.add(name)
            node = self.nodes.get(name)
            if node:
                stack.extend(node.inputs)
        return visited

    def prune(self) -> GraphSpec:
        reachable = self.reachable()
        return GraphSpec(
            nodes={name: node for name, node in self.nodes.items() if name in reachable},
            outputs=tuple(name for name in self.outputs if name in reachable),
        )
