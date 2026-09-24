import pytest
import numpy as np
from complex_reasoning.deductive_reasoning import Literal, Clause, KnowledgeBase, DeductiveEngine


class TestLiteral:
    def test_creation(self):
        lit = Literal("Rain")
        assert lit.name == "Rain"
        assert lit.negated is False

    def test_negation(self):
        lit = Literal("Rain")
        neg = -lit
        assert neg.negated is True
        assert neg.name == "Rain"

    def test_equality(self):
        assert Literal("Rain") == Literal("Rain")
        assert Literal("Rain") != Literal("Snow")

    def test_hash(self):
        assert hash(Literal("Rain")) == hash(Literal("Rain"))


class TestClause:
    def test_empty_clause(self):
        c = Clause([])
        assert c.is_empty()

    def test_resolve(self):
        c1 = Clause([Literal("Rain")])
        c2 = Clause([Literal("Rain", negated=True)])
        result = c1.resolve(c2, "Rain")
        assert result is not None
        assert result.is_empty()

    def test_resolve_no_match(self):
        c1 = Clause([Literal("Rain")])
        c2 = Clause([Literal("Snow")])
        result = c1.resolve(c2, "Rain")
        assert result is None


class TestKnowledgeBase:
    def test_forward_chain(self):
        kb = KnowledgeBase()
        kb.add_fact("Rain")
        kb.add_rule(Clause([Literal("Rain")]), Clause([Literal("WetGround")]))
        derived = kb.forward_chain()
        assert "WetGround" in derived

    def test_backward_chain(self):
        kb = KnowledgeBase()
        kb.add_fact("Rain")
        kb.add_rule(Clause([Literal("Rain")]), Clause([Literal("WetGround")]))
        assert kb.backward_chain("WetGround") is True
        assert kb.backward_chain("Unknown") is False

    def test_resolution(self):
        kb = KnowledgeBase()
        kb.add_clause(Clause([Literal("A")]))
        kb.add_clause(Clause([Literal("A", negated=True)]))
        goal = Clause([Literal("B")])
        assert kb.resolution(goal) is True


class TestDeductiveEngine:
    def test_add_premise(self):
        engine = DeductiveEngine()
        engine.add_premise("Rain")
        assert "Rain" in engine.kb.facts

    def test_modus_ponens(self):
        engine = DeductiveEngine()
        engine.add_premise("Rain")
        engine.add_rule(["Rain"], "WetGround")
        assert engine.modus_ponens("Rain", "WetGround") is True

    def test_prove(self):
        engine = DeductiveEngine()
        engine.add_premise("Rain")
        engine.add_rule(["Rain"], "WetGround")
        assert engine.prove("WetGround") is True

    def test_theorem_prove(self):
        engine = DeductiveEngine()
        engine.kb.add_clause(Clause([Literal("P")]))
        engine.kb.add_clause(Clause([Literal("P", negated=True)]))
        assert engine.theorem_prove(Clause([Literal("Q")])) is True
