"""Tests for serialization - expanded coverage."""

from __future__ import annotations

import json

import pytest

from astrovox.serialization import GraphSpec, GraphNodeSpec


def test_graph_spec_empty_json():
    spec = GraphSpec()
    data = spec.to_json()
    loaded = GraphSpec.from_json(data)
    assert loaded.nodes == {}
    assert loaded.outputs == ()


def test_graph_spec_multiple_outputs():
    spec = GraphSpec()
    spec.add_node(GraphNodeSpec(name="a", op="constant", attrs={"value": 1}))
    spec.add_node(GraphNodeSpec(name="b", op="constant", attrs={"value": 2}))
    spec.outputs = ("a", "b")
    data = spec.to_json()
    loaded = GraphSpec.from_json(data)
    assert loaded.outputs == ("a", "b")


def test_graph_node_spec_defaults():
    node = GraphNodeSpec(name="x", op="constant")
    assert node.inputs == ()
    assert node.attrs == {}


def test_graph_spec_prune_keeps_reachable():
    spec = GraphSpec()
    spec.add_node(GraphNodeSpec(name="x", op="constant", attrs={"value": 1}))
    spec.add_node(GraphNodeSpec(name="y", op="constant", attrs={"value": 2}, inputs=("x",)))
    spec.outputs = ("y",)
    pruned = spec.prune()
    assert "x" in pruned.nodes
    assert "y" in pruned.nodes
