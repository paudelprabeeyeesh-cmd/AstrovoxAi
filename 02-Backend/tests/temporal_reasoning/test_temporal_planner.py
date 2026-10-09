import pytest
from temporal_reasoning.temporal_planner import TemporalEvent, TemporalConstraint, TemporalPlanner


class TestTemporalEvent:
    def test_duration_positive(self):
        ev = TemporalEvent(event_id="e1", start=0.0, end=5.0)
        assert ev.duration() == 5.0

    def test_duration_zero(self):
        ev = TemporalEvent(event_id="e2", start=1.0, end=1.0)
        assert ev.duration() == 0.0

    def test_duration_negative_clamped(self):
        ev = TemporalEvent(event_id="e3", start=5.0, end=2.0)
        assert ev.duration() == 0.0


class TestTemporalConstraint:
    def test_before_satisfied(self):
        c = TemporalConstraint(constraint_id="c1", source="a", target="b", relation="before", min_gap=2.0)
        assert c.is_satisfied({"a": (0.0, 1.0), "b": (3.0, 4.0)})

    def test_before_unsatisfied(self):
        c = TemporalConstraint(constraint_id="c2", source="a", target="b", relation="before", min_gap=2.0)
        assert not c.is_satisfied({"a": (0.0, 1.0), "b": (1.5, 2.5)})

    def test_after_satisfied(self):
        c = TemporalConstraint(constraint_id="c3", source="a", target="b", relation="after", min_gap=1.0)
        assert c.is_satisfied({"a": (5.0, 6.0), "b": (0.0, 3.0)})

    def test_during_satisfied(self):
        c = TemporalConstraint(constraint_id="c4", source="a", target="b", relation="during")
        assert c.is_satisfied({"a": (1.0, 2.0), "b": (0.0, 3.0)})

    def test_overlaps_satisfied(self):
        c = TemporalConstraint(constraint_id="c5", source="a", target="b", relation="overlaps")
        assert c.is_satisfied({"a": (1.0, 3.0), "b": (2.0, 4.0)})

    def test_meets_satisfied(self):
        c = TemporalConstraint(constraint_id="c6", source="a", target="b", relation="meets")
        assert c.is_satisfied({"a": (0.0, 2.0), "b": (2.0, 4.0)})

    def test_missing_times_returns_true(self):
        c = TemporalConstraint(constraint_id="c7", source="a", target="b", relation="before")
        assert c.is_satisfied({})


class TestTemporalPlanner:
    def test_add_event_returns_id(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 5.0, action="move")
        assert eid == "evt_0"
        assert planner.events[eid].action == "move"

    def test_add_constraint_returns_id(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 5.0)
        eid2 = planner.add_event(6.0, 8.0)
        cid = planner.add_constraint(eid, eid2, "before", min_gap=1.0)
        assert cid == "con_2"

    def test_validate_no_violations(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 5.0)
        eid2 = planner.add_event(6.0, 8.0)
        planner.add_constraint(eid, eid2, "before", min_gap=1.0)
        assert planner.validate() == []

    def test_validate_with_violations(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 5.0)
        eid2 = planner.add_event(5.0, 8.0)
        planner.add_constraint(eid, eid2, "before", min_gap=2.0)
        assert len(planner.validate()) == 1

    def test_generate_schedule(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 3.0, action="A")
        eid2 = planner.add_event(3.0, 6.0, action="B")
        schedule = planner.generate_schedule()
        assert len(schedule) == 2
        assert schedule[0]["action"] == "A"
        assert schedule[1]["action"] == "B"

    def test_add_event_with_metadata(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 5.0, action="move", metadata={"location": "room_a"})
        assert planner.events[eid].metadata == {"location": "room_a"}

    def test_get_times(self):
        planner = TemporalPlanner()
        eid = planner.add_event(1.0, 4.0)
        assert planner.get_times()[eid] == (1.0, 4.0)

    def test_generate_schedule_with_violations(self):
        planner = TemporalPlanner()
        eid = planner.add_event(0.0, 3.0, action="A")
        eid2 = planner.add_event(3.0, 6.0, action="B")
        planner.add_constraint(eid, eid2, "before", min_gap=2.0)
        schedule = planner.generate_schedule()
        assert len(schedule[0]["violations"]) == 1

    def test_empty_planner(self):
        planner = TemporalPlanner()
        assert planner.validate() == []
        assert planner.generate_schedule() == []

    def test_constraint_max_gap_stored(self):
        c = TemporalConstraint(constraint_id="c8", source="a", target="b", relation="before", min_gap=1.0, max_gap=3.0)
        assert c.max_gap == 3.0
        assert c.min_gap == 1.0
