import pytest
from reasoning_engine.inductive_reasoner import InductiveReasoner


def test_add_observation():
    ir = InductiveReasoner()
    ir.add_observation({"x": 1}, "A")
    assert len(ir._observations) == 1


def test_generalize_uniform():
    ir = InductiveReasoner()
    ir.add_observation({"x": 1}, "A")
    ir.add_observation({"x": 2}, "A")
    pattern = ir.generalize()
    assert pattern is not None
    assert pattern["label"] == "A"
    assert pattern["confidence"] == 1.0


def test_generalize_mixed():
    ir = InductiveReasoner()
    ir.add_observation({"x": 1}, "A")
    ir.add_observation({"x": 2}, "B")
    pattern = ir.generalize()
    assert pattern is None


def test_predict_with_pattern():
    ir = InductiveReasoner()
    ir.add_observation({"x": 1}, "A")
    ir.add_observation({"x": 2}, "A")
    ir.generalize()
    label = ir.predict({"x": 3})
    assert label == "A"


def test_predict_without_pattern():
    ir = InductiveReasoner()
    label = ir.predict({"x": 1})
    assert label is None
