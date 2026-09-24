import pytest
import numpy as np
from complex_reasoning.inductive_reasoning import Example, InductiveHypothesis, InductiveEngine


class TestExample:
    def test_creation(self):
        ex = Example({"size": 1.0, "color": 0.5}, label="A", weight=2.0)
        assert ex.label == "A"
        assert ex.weight == 2.0

    def test_distance(self):
        ex1 = Example({"x": 1.0, "y": 2.0})
        ex2 = Example({"x": 4.0, "y": 6.0})
        assert ex1.distance_to(ex2) == pytest.approx(5.0)


class TestInductiveHypothesis:
    def test_add_support(self):
        h = InductiveHypothesis("Big")
        h.add_support()
        assert h.support == 1
        assert h.confidence == pytest.approx(0.5)

    def test_update_coverage(self):
        h = InductiveHypothesis("Big")
        h.add_support()
        h.update_coverage(10)
        assert h.coverage == pytest.approx(0.1)


class TestInductiveEngine:
    def test_add_example(self):
        engine = InductiveEngine()
        engine.add_example(Example({"size": 1.0}, label="A"))
        assert len(engine.examples) == 1

    def test_find_frequent_patterns(self):
        engine = InductiveEngine()
        engine.add_example(Example({"a": 1.0, "b": 0.0}, label="X"))
        engine.add_example(Example({"a": 1.0, "b": 1.0}, label="Y"))
        patterns = engine.find_frequent_patterns(min_support=0.5)
        assert any(p.description == "a" for p in patterns)

    def test_generalize(self):
        engine = InductiveEngine()
        engine.add_example(Example({"f1": 1.0, "f2": 0.0}, label="A"))
        engine.add_example(Example({"f1": 1.0, "f2": 1.0}, label="B"))
        gens = engine.generalize()
        assert isinstance(gens, list)

    def test_space_analysis(self):
        engine = InductiveEngine()
        engine.add_example(Example({"x": 1.0, "y": 2.0}))
        engine.add_example(Example({"x": 3.0, "y": 4.0}))
        stats = engine.space_analysis()
        assert "variance" in stats
        assert "mean" in stats
        assert "dim" in stats

    def test_logical_operation_gt(self):
        engine = InductiveEngine()
        engine.add_example(Example({"temp": 0.3}, label="C"))
        engine.add_example(Example({"temp": 0.8}, label="H"))
        results = engine.logical_operation("gt", "temp", 0.5)
        assert len(results) == 1
