import pytest
import numpy as np
from complex_reasoning.commonsense_reasoning import CommonsenseFact, DefaultRule, CommonsenseKnowledgeBase, CommonsenseEngine


class TestCommonsenseFact:
    def test_apply_match(self):
        fact = CommonsenseFact("Bird", "can", "fly", confidence=0.9)
        assert fact.apply("Bird", "fly") is True

    def test_apply_no_match(self):
        fact = CommonsenseFact("Bird", "can", "fly")
        assert fact.apply("Fish", "swim") is False

    def test_override_by_exception(self):
        base = CommonsenseFact("Bird", "can", "fly", confidence=0.9)
        exc = CommonsenseFact("Penguin", "can", "fly", confidence=0.9)
        base.add_exception(exc)
        assert base.apply("Penguin", "fly") is False

    def test_confidence_threshold(self):
        fact = CommonsenseFact("X", "is", "Y", confidence=0.3)
        assert fact.apply("X", "Y") is False


class TestDefaultRule:
    def test_can_override(self):
        rule = DefaultRule("if x", "then y", default=True, confidence=0.9)
        assert rule.can_override() is True

    def test_confidence_value(self):
        rule = DefaultRule("if x", "then y", confidence=0.95)
        assert rule.confidence() == pytest.approx(0.95)


class TestCommonsenseKnowledgeBase:
    def test_add_and_query(self):
        kb = CommonsenseKnowledgeBase()
        kb.add_fact(CommonsenseFact("Bird", "can", "fly"))
        result = kb.query("Bird", "fly")
        assert result is not None
        assert result.predicate == "can"

    def test_query_with_context(self):
        kb = CommonsenseKnowledgeBase()
        kb.add_fact(CommonsenseFact("Bird", "can", "fly", context="sky"))
        result = kb.query("Bird", "fly", context="sky")
        assert result is not None

    def test_query_missing(self):
        kb = CommonsenseKnowledgeBase()
        assert kb.query("Bird", "fly") is None

    def test_inference(self):
        kb = CommonsenseKnowledgeBase()
        kb.add_fact(CommonsenseFact("Bird", "can", "fly"))
        results = kb.inference("Bird", "fly")
        assert len(results) == 1

    def test_model_confidence(self):
        kb = CommonsenseKnowledgeBase()
        kb.add_fact(CommonsenseFact("Bird", "can", "fly", confidence=0.8))
        kb.add_fact(CommonsenseFact("Bird", "needs", "water", confidence=0.9))
        assert kb.model_confidence("Bird") == pytest.approx(0.85)

    def test_non_monotonic_update(self):
        kb = CommonsenseKnowledgeBase()
        f1 = CommonsenseFact("Bird", "can", "fly", confidence=0.9)
        kb.add_fact(f1)
        f2 = CommonsenseFact("Bird", "can", "fly", confidence=0.3)
        result = kb.non_monotonic(f1, f2)
        assert result is True
        assert f1.confidence == pytest.approx(0.3)


class TestCommonsenseEngine:
    def test_add_fact_and_query(self):
        engine = CommonsenseEngine()
        engine.add_fact(CommonsenseFact("Dog", "needs", "water"))
        result = engine.query("Dog", "water")
        assert result is not None
        assert result.subject == "Dog"

    def test_inference(self):
        engine = CommonsenseEngine()
        engine.add_fact(CommonsenseFact("Cat", "needs", "food"))
        results = engine.inference("Cat", "food")
        assert len(results) == 1

    def test_model_confidence(self):
        engine = CommonsenseEngine()
        engine.add_fact(CommonsenseFact("Cat", "needs", "food", confidence=0.9))
        assert engine.model_confidence("Cat") == pytest.approx(0.9)

    def test_non_monotonic(self):
        engine = CommonsenseEngine()
        f1 = CommonsenseFact("X", "is", "Y", confidence=0.9)
        engine.add_fact(f1)
        f2 = CommonsenseFact("X", "is", "Y", confidence=0.4)
        assert engine.non_monotonic(f1, f2) is True
