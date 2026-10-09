import pytest
from resource_management import PriorityScheduler


def test_higher_priority_comes_first():
    scheduler = PriorityScheduler()
    scheduler.add(2, "low")
    scheduler.add(1, "high")
    scheduler.add(3, "highest")
    assert scheduler.next() == "highest"
    assert scheduler.next() == "low"
    assert scheduler.next() == "high"


def test_empty_next_returns_none():
    scheduler = PriorityScheduler()
    assert scheduler.next() is None


def test_len_tracks_items():
    scheduler = PriorityScheduler()
    scheduler.add(1, "a")
    scheduler.add(2, "b")
    assert len(scheduler) == 2


def test_same_priority_items():
    scheduler = PriorityScheduler()
    scheduler.add(1, "a")
    scheduler.add(1, "b")
    scheduler.add(1, "c")
    items = [scheduler.next() for _ in range(3)]
    assert set(items) == {"a", "b", "c"}
    assert len(scheduler) == 0


def test_next_after_sequential_adds():
    scheduler = PriorityScheduler()
    scheduler.add(1, "low")
    scheduler.add(3, "high")
    scheduler.add(2, "medium")
    assert scheduler.next() == "high"
    assert scheduler.next() == "medium"
    assert scheduler.next() == "low"
    assert scheduler.next() is None


def test_len_decreases_after_next():
    scheduler = PriorityScheduler()
    scheduler.add(1, "a")
    scheduler.add(2, "b")
    assert len(scheduler) == 2
    scheduler.next()
    assert len(scheduler) == 1
    scheduler.next()
    assert len(scheduler) == 0
