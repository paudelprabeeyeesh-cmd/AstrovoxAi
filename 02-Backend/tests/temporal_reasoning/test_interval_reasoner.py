import pytest
from temporal_reasoning.interval_reasoner import Interval, IntervalReasoner


class TestInterval:
    def test_length(self):
        i = Interval(start=0.0, end=5.0)
        assert i.length() == 5.0

    def test_overlaps_true(self):
        a = Interval(start=0.0, end=3.0)
        b = Interval(start=2.0, end=5.0)
        assert a.overlaps(b)

    def test_overlaps_false(self):
        a = Interval(start=0.0, end=2.0)
        b = Interval(start=3.0, end=5.0)
        assert not a.overlaps(b)

    def test_contains(self):
        a = Interval(start=0.0, end=5.0)
        b = Interval(start=1.0, end=4.0)
        assert a.contains(b)
        assert not b.contains(a)

    def test_meets(self):
        a = Interval(start=0.0, end=2.0)
        b = Interval(start=2.0, end=4.0)
        assert a.meets(b)

    def test_before(self):
        a = Interval(start=0.0, end=2.0)
        b = Interval(start=3.0, end=5.0)
        assert a.before(b)

    def test_after(self):
        a = Interval(start=3.0, end=5.0)
        b = Interval(start=0.0, end=2.0)
        assert a.after(b)

    def test_equals(self):
        a = Interval(start=0.0, end=2.0)
        b = Interval(start=0.0, end=2.0)
        assert a.equals(b)

    def test_invalid_interval_raises(self):
        with pytest.raises(ValueError):
            Interval(start=5.0, end=1.0)


class TestIntervalReasoner:
    def test_add_interval(self):
        ir = IntervalReasoner()
        iid = ir.add_interval(0.0, 5.0, label="work")
        assert iid == "int_0"
        assert ir.intervals[iid].label == "work"

    def test_add_invalid_interval_raises(self):
        ir = IntervalReasoner()
        with pytest.raises(ValueError):
            ir.add_interval(5.0, 1.0)

    def test_query_relations_empty(self):
        ir = IntervalReasoner()
        iid = ir.add_interval(0.0, 5.0)
        relations = ir.query_relations(iid)
        assert relations["overlaps"] == []

    def test_query_relations_overlaps(self):
        ir = IntervalReasoner()
        iid1 = ir.add_interval(0.0, 3.0)
        iid2 = ir.add_interval(2.0, 5.0)
        relations = ir.query_relations(iid1)
        assert iid2 in relations["overlaps"]

    def test_query_relations_contains(self):
        ir = IntervalReasoner()
        iid1 = ir.add_interval(0.0, 5.0)
        iid2 = ir.add_interval(1.0, 4.0)
        relations = ir.query_relations(iid1)
        assert iid2 in relations["contains"]

    def test_merge_overlapping(self):
        ir = IntervalReasoner()
        ir.add_interval(0.0, 2.0)
        ir.add_interval(1.0, 3.0)
        ir.add_interval(4.0, 5.0)
        merged = ir.merge_overlapping()
        assert len(merged) == 2
        assert merged[0].start == 0.0
        assert merged[0].end == 3.0

    def test_gaps(self):
        ir = IntervalReasoner()
        ir.add_interval(0.0, 2.0)
        ir.add_interval(3.0, 5.0)
        gaps = ir.gaps()
        assert len(gaps) == 1
        assert gaps[0] == (2.0, 3.0)

    def test_no_gaps(self):
        ir = IntervalReasoner()
        ir.add_interval(0.0, 2.0)
        ir.add_interval(2.0, 4.0)
        assert ir.gaps() == []
