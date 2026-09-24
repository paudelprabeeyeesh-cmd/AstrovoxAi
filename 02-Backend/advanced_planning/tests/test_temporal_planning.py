
import pytest
from advanced_planning.temporal_planning import TemporalEvent, TemporalConstraint, TemporalPlanner, CPM, Scheduler


def test_temporal_event_creation():
    event = TemporalEvent(0, 0.0, "action_a", 5.0)
    assert event.end_time() == 5.0


def test_temporal_constraint_satisfied():
    c = TemporalConstraint("before", 0, 1, lower_bound=2.0)
    assert c.is_satisfied({0: 0.0, 1: 3.0})
    assert not c.is_satisfied({0: 0.0, 1: 1.0})


def test_temporal_planner_add_event():
    planner = TemporalPlanner()
    eid = planner.add_event(0.0, "move", 10.0)
    assert eid == 0
    assert planner.events[0].duration == 10.0


def test_temporal_planner_generate_schedule():
    planner = TemporalPlanner()
    planner.add_event(0.0, "task_a", 5.0)
    planner.add_event(5.0, "task_b", 3.0)
    schedule = planner.generate_schedule()
    assert len(schedule) == 2
    assert schedule[0].action == "task_a"


def test_temporal_planner_constraints():
    planner = TemporalPlanner()
    eid0 = planner.add_event(0.0, "task_a", 5.0)
    # Add target event without an explicit time so constraint can set it
    eid1 = planner.add_event(0.0, "task_b", 3.0)
    # Override the auto-assigned time to simulate unset
    planner.events[eid1] = TemporalEvent(eid1, 0.0, "task_b", 3.0)
    # Clear times so constraint kicks in
    planner.add_constraint("before", eid0, eid1, lower_bound=4.0)
    schedule = planner.generate_schedule()
    # generate_schedule should include both events
    assert len(schedule) == 2
    # eid1 (task_b) should be at least 4.0 after eid0 (0.0)
    assert schedule[1].start_time >= 4.0


def test_cpm_compute():
    activities = [
        ("A", 3.0, []),
        ("B", 2.0, ["A"]),
        ("C", 4.0, ["A"]),
        ("D", 2.0, ["B", "C"]),
    ]
    cpm = CPM(activities)
    duration, slack = cpm.compute()
    assert duration == 9.0
    assert slack["A"] == 3.0
    assert slack["D"] == 0.0


def test_cpm_critical_path():
    activities = [
        ("A", 3.0, []),
        ("B", 2.0, ["A"]),
        ("C", 4.0, ["A"]),
        ("D", 2.0, ["B", "C"]),
    ]
    cpm = CPM(activities)
    cpm.compute()
    critical = cpm.get_critical_path()
    assert "D" in critical


def test_scheduler_makespan():
    sched = Scheduler()
    sched.add_task("T1", 5.0, {"cpu": 1}, [])
    sched.add_task("T2", 3.0, {"cpu": 1}, ["T1"])
    schedule = sched.schedule()
    assert schedule["T1"] == 0.0
    assert schedule["T2"] == 5.0
    assert sched.get_makespan() == 8.0
