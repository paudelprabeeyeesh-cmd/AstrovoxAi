import pytest
from reasoning_engine.abductive_reasoner import AbductiveReasoner


def test_add_observation():
    ar = AbductiveReasoner()
    ar.add_observation("grass is wet")
    assert "grass is wet" in ar._observations


def test_add_hypothesis():
    ar = AbductiveReasoner()
    ar.add_hypothesis("rained", "grass is wet", 0.8)
    assert len(ar._hypotheses) == 1


def test_explain():
    ar = AbductiveReasoner()
    ar.add_observation("grass is wet")
    ar.add_hypothesis("rained", "grass is wet", 0.8)
    ar.add_hypothesis("sprinklers", "grass is wet", 0.5)
    candidates = ar.explain("grass is wet")
    assert len(candidates) == 2
    assert candidates[0][0] == "rained"


def test_best_explanation():
    ar = AbductiveReasoner()
    ar.add_observation("grass is wet")
    ar.add_hypothesis("rained", "grass is wet", 0.8)
    best = ar.best_explanation("grass is wet")
    assert best == "rained"


def test_no_explanation():
    ar = AbductiveReasoner()
    ar.add_observation("A")
    ar.add_hypothesis("H", "B", 0.9)
    assert ar.best_explanation("A") is None
