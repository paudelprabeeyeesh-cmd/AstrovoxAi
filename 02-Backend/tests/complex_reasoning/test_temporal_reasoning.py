import pytest
from datetime import datetime, timedelta
from complex_reasoning.temporal_reasoning import Fluent, Event, Action, EventCalculus, TemporalEngine


class TestFluent:
    def test_update(self):
        f = Fluent("Raining", truth_value=False)
        f.update(True)
        assert f.truth_value is True


class TestEvent:
    def test_applies_at(self):
        t = datetime(2024, 1, 1, 12, 0, 0)
        ev = Event("RainStart", t, [("Raining", True)], duration=timedelta(hours=1))
        assert ev.applies_at(t + timedelta(minutes=30))
        assert not ev.applies_at(t + timedelta(hours=2))


class TestEventCalculus:
    def test_holds_at_initial(self):
        ec = EventCalculus()
        ec.add_fluent("Raining", initial=False)
        assert ec.holds_at("Raining", datetime(2024, 1, 1)) is False

    def test_event_changes_fluent(self):
        ec = EventCalculus()
        ec.add_fluent("Raining", initial=False)
        t = datetime(2024, 1, 1, 12, 0, 0)
        ec.record_event(Event("RainStart", t, [("Raining", True)]))
        assert ec.holds_at("Raining", t + timedelta(minutes=1)) is True

    def test_time_to(self):
        ec = EventCalculus()
        ec.add_fluent("Raining", initial=False)
        t = datetime(2024, 1, 1, 12, 0, 0)
        ec.record_event(Event("RainStart", t, [("Raining", True)]))
        result = ec.time_to("Raining")
        assert result is not None

    def test_event_to(self):
        ec = EventCalculus()
        t1 = datetime(2024, 1, 1, 12, 0, 0)
        t2 = datetime(2024, 1, 1, 13, 0, 0)
        ec.record_event(Event("RainStart", t1, []))
        ec.record_event(Event("RainStart", t2, []))
        assert ec.event_to("RainStart") == [t1, t2]


class TestTemporalEngine:
    def test_holds_at(self):
        engine = TemporalEngine()
        t = datetime(2024, 1, 1, 12, 0, 0)
        engine.event_calculus.add_fluent("Raining", initial=False)
        engine.event_calculus.record_event(Event("RainStart", t, [("Raining", True)]))
        assert engine.holds_at("Raining", t + timedelta(minutes=1)) is True

    def test_time_to(self):
        engine = TemporalEngine()
        t = datetime(2024, 1, 1, 12, 0, 0)
        engine.event_calculus.add_fluent("Raining", initial=False)
        engine.event_calculus.record_event(Event("RainStart", t, [("Raining", True)]))
        assert engine.time_to("Raining") is not None
