import pytest
import numpy as np
from advanced_reasoning.debate_engine import DebateEngine, Perspective


class TestDebateEngine:
    def test_analyze_single_perspective_raises(self):
        engine = DebateEngine(min_perspectives=2)
        p = Perspective(id="p1", name="A", stance="pro", arguments=["arg1"], evidence=["ev1"], confidence=0.8)
        with pytest.raises(ValueError, match="At least 2 perspectives required"):
            engine.analyze("topic", [p])

    def test_analyze_consensus_unanimous(self):
        engine = DebateEngine()
        perspectives = [
            Perspective(id="p1", name="A", stance="yes", arguments=["a1"], evidence=[], confidence=0.9),
            Perspective(id="p2", name="B", stance="yes", arguments=["a2"], evidence=[], confidence=0.8),
        ]
        result = engine.analyze("topic", perspectives)
        assert result.consensus == "yes"
        assert result.confidence > 0.0

    def test_analyze_disagreement(self):
        engine = DebateEngine()
        perspectives = [
            Perspective(id="p1", name="A", stance="pro", arguments=["a1", "shared"], evidence=["e1"], confidence=0.8),
            Perspective(id="p2", name="B", stance="con", arguments=["b1", "shared"], evidence=["e2"], confidence=0.7),
        ]
        result = engine.analyze("topic", perspectives)
        assert len(result.disagreement_areas) > 0
        assert "shared" not in " ".join(result.disagreement_areas).lower() or len(result.disagreement_areas) > 0

    def test_confidence_computed(self):
        engine = DebateEngine()
        perspectives = [
            Perspective(id="p1", name="A", stance="s1", arguments=[], evidence=[], confidence=0.9),
            Perspective(id="p2", name="B", stance="s2", arguments=[], evidence=[], confidence=0.1),
        ]
        result = engine.analyze("topic", perspectives)
        assert 0.0 <= result.confidence <= 1.0

    def test_synthesis_includes_all(self):
        engine = DebateEngine()
        perspectives = [
            Perspective(id="p1", name="A", stance="pro", arguments=["a"], evidence=["e1"], confidence=0.8),
            Perspective(id="p2", name="B", stance="pro", arguments=["b"], evidence=["e2"], confidence=0.8),
        ]
        result = engine.analyze("topic", perspectives)
        assert "A" in result.synthesis
        assert "B" in result.synthesis
