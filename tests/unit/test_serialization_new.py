"""Tests for serialization - expanded coverage."""

from __future__ import annotations

import json

import pytest

from astrovox.serialization import GraphSpec, GraphNodeSpec


def test_graph_spec_from_json_empty():
    spec = GraphSpec.from_json("{}")
    assert spec.nodes == {}
    assert spec.outputs == ()


def test_graph_spec_node_equality():
    a = GraphNodeSpec(name="x", op="constant", attrs={"value": 1})
    b = GraphNodeSpec(name="x", op="constant", attrs={"value": 1})
    assert a.name == b.name
    assert a.op == b.op
    assert a.attrs == b.attrs


def test_graph_spec_prune_keeps_outputs():
    spec = GraphSpec()
    spec.add_node(GraphNodeSpec(name="x", op="constant", attrs={"value": 1}))
    spec.outputs = ("x",)
    pruned = spec.prune()
    assert pruned.outputs == ("x",)
