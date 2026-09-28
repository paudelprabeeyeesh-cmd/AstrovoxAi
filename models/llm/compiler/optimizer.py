from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Tuple

from models.llm.compiler.graph import ComputationGraph, Edge, Node


class CompilerPass(ABC):
    @abstractmethod
    def run(self, graph: ComputationGraph) -> ComputationGraph:
        raise NotImplementedError


class FusionPass(CompilerPass):
    def run(self, graph: ComputationGraph) -> ComputationGraph:
        fused = ComputationGraph()
        node_map: Dict[NodeId, NodeId] = {}
        for node in graph.nodes.values():
            new_id = node.id
            fused.add_node(node)
            node_map[node.id] = new_id
        for edge in graph.edges:
            new_edge = Edge(source=node_map[edge.source], target=node_map[edge.target])
            fused.add_edge(new_edge)
        fused.set_outputs([node_map[nid] for nid in graph.outputs()])
        return fused


class DeadCodeEliminator(CompilerPass):
    def run(self, graph: ComputationGraph) -> ComputationGraph:
        live: set = set(graph.outputs())
        changed = True
        while changed:
            changed = False
            for edge in graph.edges:
                if edge.target in live and edge.source not in live:
                    live.add(edge.source)
                    changed = True
        pruned = ComputationGraph()
        for node in graph.nodes.values():
            if node.id in live:
                pruned.add_node(node)
        for edge in graph.edges:
            if edge.source in live and edge.target in live:
                pruned.add_edge(edge)
        pruned.set_outputs([nid for nid in graph.outputs() if nid in live])
        return pruned


class ConstantFolder(CompilerPass):
    def run(self, graph: ComputationGraph) -> ComputationGraph:
        optimized = ComputationGraph()
        node_map: Dict[NodeId, NodeId] = {}
        for node in graph.nodes.values():
            if self._is_constant(node) and not self._is_leaf(node, graph):
                folded = self._fold(node, graph)
                optimized.add_node(folded)
                node_map[node.id] = folded.id
            else:
                optimized.add_node(node)
                node_map[node.id] = node.id
        for edge in graph.edges:
            new_edge = Edge(source=node_map[edge.source], target=node_map[edge.target])
            optimized.add_edge(new_edge)
        optimized.set_outputs([node_map[nid] for nid in graph.outputs()])
        return optimized

    def _is_constant(self, node: Node) -> bool:
        return node.op == "const"

    def _is_leaf(self, node: Node, graph: ComputationGraph) -> bool:
        return False

    def _fold(self, node: Node, graph: ComputationGraph) -> Node:
        return Node(id=node.id, op="const_folded", attrs=dict(node.attrs), shape=node.shape, dtype=node.dtype)


class MemoryOptimizer(CompilerPass):
    def run(self, graph: ComputationGraph) -> ComputationGraph:
        optimized = ComputationGraph()
        node_map: Dict[NodeId, NodeId] = {}
        for node in graph.nodes.values():
            optimized.add_node(node)
            node_map[node.id] = node.id
        for edge in graph.edges:
            new_edge = Edge(source=node_map[edge.source], target=node_map[edge.target])
            optimized.add_edge(new_edge)
        optimized.set_outputs([node_map[nid] for nid in graph.outputs()])
        return optimized
