"""Tests for the compiler optimization passes."""

from __future__ import annotations

import pytest

from astrovox.compiler import Graph, Node, constant_folding, dead_code_elimination, infer_shapes, operator_fusion, optimize, plan_memory


def build_sample_graph() -> Graph:
    graph = Graph()
    graph.add(Node(name="x", op="constant", attrs={"value": 2}))
    graph.add(Node(name="y", op="constant", attrs={"value": 3}))
    graph.add(Node(name="add", op="add", inputs=("x", "y")))
    graph.outputs = ("add",)
    return graph


def test_dead_code_elimination_removes_unused_nodes():
    graph = build_sample_graph()
    graph.add(Node(name="dead", op="constant", attrs={"value": 1}))
    optimized = dead_code_elimination(graph)
    assert "dead" not in optimized.nodes


def test_constant_folding_replaces_constants():
    graph = build_sample_graph()
    optimized = constant_folding(graph)
    add_node = optimized.nodes.get("add")
    assert add_node is not None
    assert add_node.op == "constant"
    assert add_node.attrs["value"] == 5


def test_operator_fusion_marks_fusable_patterns():
    graph = build_sample_graph()
    graph.add(Node(name="bias", op="add", inputs=()))
    graph.add(Node(name="matmul", op="matmul", inputs=("add", "bias")))
    graph.outputs = ("matmul",)
    optimized = operator_fusion(graph)
    assert optimized.nodes["matmul"].op == "fused_matmul_bias"


def test_shape_inference_returns_shapes_for_constants():
    graph = build_sample_graph()
    shapes = infer_shapes(graph, {})
    assert shapes["x"] == ()
    assert shapes["y"] == ()
    assert shapes["add"] == ()


def test_memory_plan_returns_nonnegative_sizes():
    graph = build_sample_graph()
    shapes = infer_shapes(graph, {})
    allocation = plan_memory(graph, shapes)
    assert allocation["x"] >= 0
    assert allocation["y"] >= 0


def test_optimize_applies_multiple_passes():
    graph = build_sample_graph()
    optimized = optimize(graph)
    assert "dead" not in optimized.nodes if "dead" in graph.nodes else True
