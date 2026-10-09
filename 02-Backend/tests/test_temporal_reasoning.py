import pytest
from world_model.temporal_reasoning import TemporalReasoner, Event


class TestTemporalReasoner:
    def test_add_and_sequence(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=1.0, description="start"))
        tr.add_event(Event(id="e2", timestamp=2.0, description="middle"))
        tr.add_event(Event(id="e3", timestamp=3.0, description="end"))
        seq = tr.sequence(1.5, 2.5)
        assert len(seq) == 1
        assert seq[0].id == "e2"

    def test_causality_score_with_link(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=1.0, description="cause"))
        tr.add_event(Event(id="e2", timestamp=2.0, description="effect"))
        tr.add_causal_link("e1", "e2", strength=0.8)
        assert tr.causality_score("e1", "e2") == pytest.approx(0.8)

    def test_causality_score_without_link(self):
        tr = TemporalReasoner()
        assert tr.causality_score("e1", "e2") == 0.0

    def test_predict_next(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=1.0, description="x"))
        predicted = tr.predict_next()
        assert predicted is not None
        assert predicted.timestamp == 2.0

    def test_build_timeline(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=1.0, description="a"))
        tr.add_event(Event(id="e2", timestamp=2.0, description="b"))
        tr.add_causal_link("e1", "e2")
        timeline = tr.build_timeline()
        assert len(timeline) == 2
        assert timeline[1]["causes"] == ["e1"]

    def test_event_similarity(self):
        tr = TemporalReasoner()
        a = Event(id="a", timestamp=1.0, description="d", entities=["x"])
        b = Event(id="b", timestamp=1.1, description="d", entities=["x"])
        assert tr.event_similarity(a, b) > 0.0
