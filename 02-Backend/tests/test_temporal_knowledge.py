import pytest
from datetime import datetime, timedelta
import numpy as np
from knowledge_graph.temporal_knowledge import TemporalKnowledgeBase, TemporalFact


class TestTemporalKnowledge:
    def test_add_and_query_at(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(
            TemporalFact(
                id="f1", subject="s1", predicate="p1", object="o1",
                start_time=datetime(2020, 1, 1), end_time=datetime(2021, 1, 1), confidence=0.9,
            )
        )
        results = tk.query_at("s1", "p1", datetime(2020, 6, 1))
        assert len(results) == 1

    def test_query_outside_interval(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(
            TemporalFact(
                id="f1", subject="s1", predicate="p1", object="o1",
                start_time=datetime(2020, 1, 1), end_time=datetime(2021, 1, 1),
            )
        )
        results = tk.query_at("s1", "p1", datetime(2022, 1, 1))
        assert len(results) == 0

    def test_query_interval(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(
            TemporalFact(
                id="f1", subject="s1", predicate="p1", object="o1",
                start_time=datetime(2020, 1, 1), end_time=datetime(2022, 1, 1),
            )
        )
        results = tk.query_interval("s1", "p1", datetime(2021, 1, 1), datetime(2023, 1, 1))
        assert len(results) == 1

    def test_temporal_overlap(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(TemporalFact(id="f1", subject="s", predicate="p", object="o", start_time=datetime(2020, 1, 1), end_time=datetime(2021, 1, 1)))
        tk.add_fact(TemporalFact(id="f2", subject="s", predicate="p", object="o", start_time=datetime(2020, 6, 1), end_time=datetime(2020, 9, 1)))
        overlap = tk.temporal_overlap("f1", "f2")
        assert 0.0 < overlap <= 1.0

    def test_temporal_distance(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(TemporalFact(id="f1", subject="s", predicate="p", object="o", start_time=datetime(2020, 1, 1), end_time=datetime(2020, 1, 2)))
        tk.add_fact(TemporalFact(id="f2", subject="s", predicate="p", object="o", start_time=datetime(2020, 2, 1), end_time=datetime(2020, 2, 2)))
        dist = tk.temporal_distance("f1", "f2")
        assert dist is not None and dist > 0

    def test_infer_transitivity(self):
        tk = TemporalKnowledgeBase()
        tk.add_fact(TemporalFact(id="f1", subject="a", predicate="r", object="b", start_time=datetime(2020, 1, 1), end_time=datetime(2020, 6, 1)))
        tk.add_fact(TemporalFact(id="f2", subject="b", predicate="r", object="c", start_time=datetime(2020, 6, 1), end_time=datetime(2021, 1, 1)))
        inferred = tk.infer_transitivity()
        assert len(inferred) >= 1

    def test_decay_confidence(self):
        tk = TemporalKnowledgeBase(default_duration=timedelta(days=1))
        tk.add_fact(TemporalFact(id="f1", subject="s", predicate="p", object="o", start_time=datetime(2020, 1, 1), confidence=1.0))
        tk.decay_confidence(datetime(2020, 1, 2), timedelta(days=1))
        assert tk.facts["f1"].confidence < 1.0
