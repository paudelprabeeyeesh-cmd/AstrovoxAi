import pytest
from temporal_reasoning.narrative_compiler import NarrativeEvent, NarrativeCompiler


class TestNarrativeCompiler:
    def test_add_event(self):
        compiler = NarrativeCompiler()
        compiler.add_event("e1", "start engine", 0.0, 1.0, entities=["engine"])
        assert "e1" in compiler.events
        assert compiler.events["e1"].text == "start engine"

    def test_resolve_order(self):
        compiler = NarrativeCompiler()
        compiler.add_event("e1", "a", 2.0, 3.0)
        compiler.add_event("e2", "b", 1.0, 2.0)
        compiler.add_event("e3", "c", 3.0, 4.0)
        assert compiler.resolve_order() == ["e2", "e1", "e3"]

    def test_filter_by_entity(self):
        compiler = NarrativeCompiler()
        compiler.add_event("e1", "a", 0.0, 1.0, entities=["robot"])
        compiler.add_event("e2", "b", 1.0, 2.0, entities=["human"])
        compiler.add_event("e3", "c", 2.0, 3.0, entities=["robot", "human"])
        filtered = compiler.filter_by_entity("robot")
        assert len(filtered) == 2
        assert filtered[0].event_id == "e1"
        assert filtered[1].event_id == "e3"

    def test_summarize(self):
        compiler = NarrativeCompiler()
        compiler.add_event("e1", "alpha", 0.0, 1.0, entities=["x"], relations=["before"])
        summary = compiler.summarize()
        assert len(summary) == 1
        assert summary[0]["text"] == "alpha"
        assert summary[0]["entities"] == ["x"]
        assert summary[0]["relations"] == ["before"]

    def test_empty_compiler(self):
        compiler = NarrativeCompiler()
        assert compiler.resolve_order() == []
        assert compiler.filter_by_entity("x") == []
        assert compiler.summarize() == []
