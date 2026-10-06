"""Tests for computation graph serialization."""

from __future__ import annotations

import json

import pytest

from astrovox.serialization import GraphSpec, GraphNodeSpec


def test_graph_spec_round_trip():
    spec = GraphSpec()
    spec.add_node(GraphNodeSpec(name="x", op="constant", attrs={"value": 1}))
    spec.add_node(GraphNodeSpec(name="y", op="constant", attrs={"value": 2}))
    spec.add_node(GraphNodeSpec(name="add", op="add", inputs=("x", "y")))
    spec.outputs = ("add",)
    data = spec.to_json()
    loaded = GraphSpec.from_json(data)
    assert "add" in loaded.nodes
    assert loaded.nodes["add"].inputs == ("x", "y")
    assert loaded.outputs == ("add",)


def test_graph_spec_prune_removes_unreachable():
    spec = GraphSpec()
    spec.add_node(GraphNodeSpec(name="x", op="constant", attrs={"value": 1}))
    spec.add_node(GraphNodeSpec(name="dead", op="constant", attrs={"value": 2}))
    spec.outputs = ("x",)
    pruned = spec.prune()
    assert "dead" not in pruned.nodes
    assert "x" in pruned.nodes
