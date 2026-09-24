import pytest
from reasoning_engine.deductive_reasoner import DeductiveReasoner


def test_add_premise():
    dr = DeductiveReasoner()
    dr.add_premise("P")
    assert "P" in dr._premises


def test_derive_success():
    dr = DeductiveReasoner()
    dr.add_premise("P")
    dr.add_rule("rule1", ["P"], "Q")
    result = dr.derive("Q")
    assert result == "Q"


def test_derive_failure():
    dr = DeductiveReasoner()
    dr.add_premise("P")
    dr.add_rule("rule1", ["P"], "Q")
    result = dr.derive("Z")
    assert result is None


def test_modus_ponens():
    dr = DeductiveReasoner()
    result = dr.apply_modus_ponens("P", ("P", "Q"))
    assert result == "Q"


def test_empty_reasoner():
    dr = DeductiveReasoner()
    assert dr.derive("Q") is None
