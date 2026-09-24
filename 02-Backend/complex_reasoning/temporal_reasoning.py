import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime, timedelta


class Fluent:
    def __init__(self, name: str, truth_value: bool = False, timestamp: Optional[datetime] = None):
        self.name = name
        self.truth_value = truth_value
        self.timestamp = timestamp or datetime.now()

    def update(self, truth_value: bool, timestamp: Optional[datetime] = None):
        self.truth_value = truth_value
        if timestamp:
            self.timestamp = timestamp


class Event:
    def __init__(self, name: str, time: datetime, effects: List[Tuple[str, bool]], duration: Optional[timedelta] = None):
        self.name = name
        self.time = time
        self.effects = effects
        self.duration = duration or timedelta(seconds=0)

    def applies_at(self, moment: datetime) -> bool:
        end = self.time + self.duration
        return self.time <= moment <= end

    def effect_at(self, fluent: str) -> Optional[bool]:
        for f, val in self.effects:
            if f == fluent:
                return val
        return None


class Action:
    def __init__(self, name: str, precondition: Dict[str, bool], effect: Dict[str, bool], duration: timedelta = timedelta(seconds=0)):
        self.name = name
        self.precondition = precondition
        self.effect = effect
        self.duration = duration

    def is_executable(self, fluents: Dict[str, bool]) -> bool:
        return all(fluents.get(k, False) == v for k, v in self.precondition.items())


class EventCalculus:
    def __init__(self):
        self.events: List[Event] = []
        self.fluents: Dict[str, Fluent] = {}
        self.initial: Dict[str, bool] = {}
        self.bounds: Tuple[datetime, datetime] = (datetime.now(), datetime.now() + timedelta(days=1))

    def add_fluent(self, name: str, initial: bool = False):
        self.fluents[name] = Fluent(name, truth_value=initial)
        self.initial[name] = initial

    def record_event(self, event: Event):
        self.events.append(event)

    def holds_at(self, fluent_name: str, moment: datetime) -> bool:
        if fluent_name not in self.fluents:
            return False
        current = self.initial.get(fluent_name, self.fluents[fluent_name].truth_value)
        for ev in sorted(self.events, key=lambda e: e.time):
            if ev.time > moment:
                break
            if ev.applies_at(moment):
                eff = ev.effect_at(fluent_name)
                if eff is not None:
                    current = eff
            elif ev.effect_at(fluent_name) is not None and ev.time <= moment:
                current = ev.effect_at(fluent_name)
        return current

    def time_to(self, fluent_name: str) -> Optional[timedelta]:
        start = self.bounds[0]
        event_times = [ev.time for ev in self.events] + list(self._time_range(start, self.bounds[1], timedelta(seconds=1)))
        for moment in sorted(set(event_times)):
            if self.holds_at(fluent_name, moment):
                return moment - start
        return None

    def _time_range(self, start: datetime, end: datetime, delta: timedelta) -> List[datetime]:
        moments = []
        current = start
        while current <= end:
            moments.append(current)
            current += delta
        return moments

    def event_to(self, event_name: str) -> List[datetime]:
        return sorted([ev.time for ev in self.events if ev.name == event_name])

    def sequence(self, event_names: List[str]) -> List[datetime]:
        seq = []
        for name in event_names:
            seq.extend(self.event_to(name))
        return sorted(seq)


class TemporalOperator:
    def __init__(self, moment: datetime, operator: str = "next"):
        self.moment = moment
        self.operator = operator

    def next_op(self, duration: timedelta) -> "TemporalOperator":
        return TemporalOperator(self.moment + duration, "next")

    def until(self, other: "TemporalOperator") -> bool:
        return self.moment <= other.moment

    def since(self, other: "TemporalOperator") -> bool:
        return self.moment >= other.moment


class TemporalEngine:
    def __init__(self):
        self.event_calculus = EventCalculus()
        self.operators: List[TemporalOperator] = []

    def holds_at(self, fluent_name: str, moment: datetime) -> bool:
        return self.event_calculus.holds_at(fluent_name, moment)

    def time_to(self, fluent_name: str) -> Optional[timedelta]:
        return self.event_calculus.time_to(fluent_name)
