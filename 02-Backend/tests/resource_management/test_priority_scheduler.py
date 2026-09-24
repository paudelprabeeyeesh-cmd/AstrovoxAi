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
