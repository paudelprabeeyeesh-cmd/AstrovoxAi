import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.transcendent_reasoning import (
    TranscendentReasoner,
    ReasoningTrace,
)


class TestTranscendentReasoner:
    def test_reason_returns_trace(self):
        reasoner = TranscendentReasoner(max_abstraction=6)
        trace = reasoner.reason("solve_world_hunger", abstraction_level=2)
        assert isinstance(trace, ReasoningTrace)
        assert trace.problem == "solve_world_hunger"
        assert trace.abstraction_level == 2
        assert len(trace.subproblems) > 0

    def test_meta_reason_improves_confidence(self):
        reasoner = TranscendentReasoner(max_abstraction=6)
        trace = reasoner.reason("climate_modeling", abstraction_level=1)
        meta = reasoner.meta_reason(trace)
        assert "optimal_abstraction" in meta
        assert "confidences" in meta
        assert len(meta["confidences"]) == reasoner.max_abstraction

    def test_detect_novelty(self):
        reasoner = TranscendentReasoner()
        novelty = reasoner.detect_novelty("entirely_new_problem")
        assert 0.0 <= novelty <= 1.0

    def test_reasoning_stats(self):
        reasoner = TranscendentReasoner()
        reasoner.reason("p1", abstraction_level=1)
        reasoner.reason("p2", abstraction_level=3)
        stats = reasoner.get_reasoning_stats()
        assert stats["traces"] == 2
        assert stats["mean_confidence"] >= 0.0

    def test_abstraction_level_bounded(self):
        reasoner = TranscendentReasoner(max_abstraction=4)
        trace = reasoner.reason("test", abstraction_level=10)
        assert trace.abstraction_level == 4
