import pytest
from datetime import datetime, timedelta
from knowledge_graph.temporal_knowledge import TemporalFact, TemporalKnowledgeBase


class TestTemporalFact:
    def test_defaults(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
        )
        assert fact.end_time is None
        assert fact.confidence == 1.0
        assert fact.source == "unknown"

    def test_custom_values(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
            confidence=0.9,
            source="web",
        )
        assert fact.end_time == datetime(2024, 12, 31)
        assert fact.confidence == 0.9
        assert fact.source == "web"


class TestTemporalKnowledgeBase:
    def setup_method(self):
        self.kb = TemporalKnowledgeBase()

    def test_add_fact(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
        )
        self.kb.add_fact(fact)
        assert "f1" in self.kb.facts
        assert "Alice" in self.kb.index

    def test_query_at_within_interval(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(fact)
        results = self.kb.query_at("Alice", "knows", datetime(2024, 6, 1))
        assert len(results) == 1
        assert results[0].id == "f1"

    def test_query_at_no_end_time(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
        )
        self.kb.add_fact(fact)
        results = self.kb.query_at("Alice", "knows", datetime(2025, 1, 1))
        assert len(results) == 1

    def test_query_at_outside_interval(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 6, 1),
        )
        self.kb.add_fact(fact)
        results = self.kb.query_at("Alice", "knows", datetime(2024, 12, 1))
        assert len(results) == 0

    def test_query_interval_overlap(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(fact)
        results = self.kb.query_interval(
            "Alice", "knows", datetime(2024, 6, 1), datetime(2024, 8, 1)
        )
        assert len(results) == 1

    def test_query_interval_no_overlap(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 3, 1),
        )
        self.kb.add_fact(fact)
        results = self.kb.query_interval(
            "Alice", "knows", datetime(2024, 6, 1), datetime(2024, 8, 1)
        )
        assert len(results) == 0

    def test_temporal_overlap_full(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Alice",
            predicate="knows",
            object="Charlie",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        overlap = self.kb.temporal_overlap("f1", "f2")
        assert overlap == 1.0

    def test_temporal_overlap_partial(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 6, 1),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Alice",
            predicate="knows",
            object="Charlie",
            start_time=datetime(2024, 3, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        overlap = self.kb.temporal_overlap("f1", "f2")
        assert 0.0 < overlap < 1.0

    def test_temporal_overlap_none(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 3, 1),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Alice",
            predicate="knows",
            object="Charlie",
            start_time=datetime(2024, 6, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        overlap = self.kb.temporal_overlap("f1", "f2")
        assert overlap == 0.0

    def test_temporal_overlap_missing_fact(self):
        assert self.kb.temporal_overlap("f1", "f2") == 0.0

    def test_temporal_distance_sequential(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 3, 1),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Bob",
            predicate="knows",
            object="Charlie",
            start_time=datetime(2024, 6, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        distance = self.kb.temporal_distance("f1", "f2")
        expected = (datetime(2024, 6, 1) - datetime(2024, 3, 1)).total_seconds()
        assert distance == expected

    def test_temporal_distance_overlapping(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 6, 1),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Bob",
            predicate="knows",
            object="Charlie",
            start_time=datetime(2024, 3, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        assert self.kb.temporal_distance("f1", "f2") == 0.0

    def test_temporal_distance_missing_fact(self):
        assert self.kb.temporal_distance("f1", "f2") is None

    def test_infer_transitivity(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 6, 1),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Bob",
            predicate="knows",
            object="Charlie",
            start_time=datetime(2024, 6, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        inferred = self.kb.infer_transitivity()
        assert len(inferred) == 1
        assert inferred[0].subject == "Alice"
        assert inferred[0].object == "Charlie"
        assert inferred[0].source == "transitivity"

    def test_infer_transitivity_no_match(self):
        f1 = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2024, 1, 1),
            end_time=datetime(2024, 6, 1),
        )
        f2 = TemporalFact(
            id="f2",
            subject="Charlie",
            predicate="knows",
            object="Dave",
            start_time=datetime(2024, 6, 1),
            end_time=datetime(2024, 12, 31),
        )
        self.kb.add_fact(f1)
        self.kb.add_fact(f2)
        assert self.kb.infer_transitivity() == []

    def test_decay_confidence(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2020, 1, 1),
            confidence=1.0,
        )
        self.kb.add_fact(fact)
        self.kb.decay_confidence(
            reference_time=datetime(2024, 1, 1), half_life=timedelta(days=365)
        )
        assert 0.0 < self.kb.facts["f1"].confidence < 1.0

    def test_decay_confidence_bounds(self):
        fact = TemporalFact(
            id="f1",
            subject="Alice",
            predicate="knows",
            object="Bob",
            start_time=datetime(2020, 1, 1),
            confidence=1.0,
        )
        self.kb.add_fact(fact)
        self.kb.decay_confidence(
            reference_time=datetime(2100, 1, 1), half_life=timedelta(days=365)
        )
        assert self.kb.facts["f1"].confidence >= 0.0
        assert self.kb.facts["f1"].confidence <= 1.0
