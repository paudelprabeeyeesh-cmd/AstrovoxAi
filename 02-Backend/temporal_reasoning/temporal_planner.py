from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TemporalEvent:
    event_id: str
    start: float
    end: float
    action: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class TemporalConstraint:
    constraint_id: str
    source: str
    target: str
    relation: str
    min_gap: float = 0.0
    max_gap: float = float("inf")

    def is_satisfied(self, times: Dict[str, Tuple[float, float]]) -> bool:
        if self.source not in times or self.target not in times:
            return True
        s_start, s_end = times[self.source]
        t_start, t_end = times[self.target]
        if self.relation == "before":
            return t_start - s_end >= self.min_gap
        elif self.relation == "after":
            return s_start - t_end >= self.min_gap
        elif self.relation == "during":
            return s_start >= t_start and s_end <= t_end
        elif self.relation == "overlaps":
            return s_start < t_end and s_end > t_start
        elif self.relation == "meets":
            return abs(s_end - t_start) <= 1e-9
        return True


class TemporalPlanner:
    def __init__(self):
        self.events: Dict[str, TemporalEvent] = {}
        self.constraints: List[TemporalConstraint] = []
        self._counter = 0

    def add_event(self, start: float, end: float, action: Any = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        event_id = f"evt_{self._counter}"
        self._counter += 1
        self.events[event_id] = TemporalEvent(event_id=event_id, start=start, end=end, action=action, metadata=metadata or {})
        return event_id

    def add_constraint(self, source: str, target: str, relation: str, min_gap: float = 0.0, max_gap: float = float("inf")) -> str:
        cid = f"con_{self._counter}"
        self._counter += 1
        self.constraints.append(TemporalConstraint(constraint_id=cid, source=source, target=target, relation=relation, min_gap=min_gap, max_gap=max_gap))
        return cid

    def get_times(self) -> Dict[str, Tuple[float, float]]:
        return {eid: (ev.start, ev.end) for eid, ev in self.events.items()}

    def validate(self) -> List[TemporalConstraint]:
        times = self.get_times()
        return [c for c in self.constraints if not c.is_satisfied(times)]

    def generate_schedule(self) -> List[Dict[str, Any]]:
        times = self.get_times()
        violations = self.validate()
        schedule = []
        for eid, ev in sorted(self.events.items(), key=lambda x: x[1].start):
            schedule.append({
                "event_id": eid,
                "action": ev.action,
                "start": ev.start,
                "end": ev.end,
                "duration": ev.duration(),
                "violations": [c.constraint_id for c in violations if c.source == eid or c.target == eid],
            })
        return schedule
