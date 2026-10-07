"""Tests for compiler - expanded coverage."""

from __future__ import annotations

import pytest

from astrovox.compiler import Graph, Node, constant_folding, dead_code_elimination, infer_shapes, operator_fusion, optimize, plan_memory


def test_dead_code_elimination_keeps_output():
    graph = Graph()
    graph.add(Node(name="x", op="constant", attrs={"value": 1}))
    graph.outputs = ("x",)
    optimized = dead_code_elimination(graph)
    assert "x" in optimized.nodes


def test_constant_folding_add():
    graph = Graph()
    graph.add(Node(name="x", op="constant", attrs={"value": 2}))
    graph.add(Node(name="y", op="constant", attrs={"value": 3}))
    graph.add(Node(name="add", op="add", inputs=("x", "y")))
    graph.outputs = ("add",)
    optimized = constant_folding(graph)
    assert optimized.nodes["add"].op == "constant"
    assert optimized.nodes["add"].attrs["value"] == 5


def test_operator_fusion_keeps_non_fusable():
    graph = Graph()
    graph.add(Node(name="x", op="constant", attrs={"value": 1}))
    graph.outputs = ("x",)
    optimized = operator_fusion(graph)
    assert "x" in optimized.nodes


def test_infer_shapes_for_matmul():
    graph = Graph()
    graph.add(Node(name="a", op="constant", attrs={"value": 1}))
    graph.add(Node(name="b", op="constant", attrs={"value": 1}))
    graph.add(Node(name="mm", op="matmul", inputs=("a", "b")))
    graph.outputs = ("mm",)
    shapes = infer_shapes(graph, {"a": (2, 3), "b": (3, 4)})
    assert shapes["mm"] == (2, 4)


def test_plan_memory_returns_bytes():
    graph = Graph()
    graph.add(Node(name="x", op="constant", attrs={"value": 1}))
    graph.outputs = ("x",)
    shapes = infer_shapes(graph, {})
    allocation = plan_memory(graph, shapes)
    assert allocation["x"] >= 0
