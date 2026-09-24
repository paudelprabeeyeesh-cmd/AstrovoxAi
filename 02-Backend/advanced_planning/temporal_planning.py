
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class TemporalEvent:
    event_id: int
    time: float
    action: Any
    duration: float = 0.0

    def end_time(self) -> float:
        return self.time + self.duration


@dataclass
class TemporalConstraint:
    type: str
    source: int
    target: int
    lower_bound: float = 0.0
    upper_bound: float = float("inf")

    def is_satisfied(self, times: Dict[int, float]) -> bool:
        if self.source not in times or self.target not in times:
            return True
        t1, t2 = times[self.source], times[self.target]
        if self.type == "before":
            return t2 - t1 >= self.lower_bound
        elif self.type == "after":
            return t1 - t2 >= self.lower_bound
        elif self.type == "during":
            return t1 <= t2 and t2 + self.upper_bound >= t1
        return True


@dataclass
class ScheduleEntry:
    action: Any
    start_time: float
    end_time: float
    resources: List[Any] = field(default_factory=list)


class TemporalPlanner:
    def __init__(self):
        self.events: Dict[int, TemporalEvent] = {}
        self.constraints: List[TemporalConstraint] = []
        self.schedule: List[ScheduleEntry] = []
        self.event_counter = 0

    def add_event(self, time: float, action: Any, duration: float = 0.0) -> int:
        event_id = self.event_counter
        self.event_counter += 1
        self.events[event_id] = TemporalEvent(event_id, time, action, duration)
        return event_id

    def add_constraint(self, ctype: str, source: int, target: int, lower_bound: float = 0.0,
                       upper_bound: float = float("inf")):
        self.constraints.append(TemporalConstraint(ctype, source, target, lower_bound, upper_bound))

    def get_candidates(self) -> List[TemporalEvent]:
        return sorted(self.events.values(), key=lambda e: e.time)

    def generate_schedule(self) -> List[ScheduleEntry]:
        sorted_events = self.get_candidates()
        times: Dict[int, float] = {}
        schedule = []
        for event in sorted_events:
            if event.event_id not in times:
                times[event.event_id] = event.time
            for constraint in self.constraints:
                if constraint.source == event.event_id and constraint.target in times:
                    times[constraint.target] = max(times.get(constraint.target, event.time),
                                                   times[event.event_id] + constraint.lower_bound)
            schedule.append(ScheduleEntry(action=event.action, start_time=times[event.event_id],
                                          end_time=event.end_time()))
        self.schedule = schedule
        return schedule


class CPM:
    def __init__(self, activities: List[Tuple[Any, float, List[Any]]]):
        self.activities = activities
        self.earliest_start: Dict[Any, float] = {}
        self.latest_start: Dict[Any, float] = {}
        self.slack: Dict[Any, float] = {}
        self._names: List[Any] = [act for act, _, _ in activities]
        self._dur: Dict[Any, float] = {act: dur for act, dur, _ in activities}
        self._preds: Dict[Any, List[Any]] = {act: list(preds) for act, _, preds in activities}
        self._succs: Dict[Any, List[Any]] = {act: [] for act, _, _ in activities}
        for act, _, preds in activities:
            for p in preds:
                if p in self._succs:
                    self._succs[p].append(act)

    def compute(self) -> Tuple[float, Dict[Any, float]]:
        if not self.activities:
            return 0.0, {}
        es = {act: 0.0 for act in self._names}
        order = self._topological_sort()
        for act in order:
            for succ in self._succs.get(act, []):
                es[succ] = max(es[succ], es[act] + self._dur[act])
        project_duration = max(es[act] + self._dur[act] for act in self._names)
        ls = {act: project_duration for act in self._names}
        for act in reversed(order):
            for succ in self._succs.get(act, []):
                ls[act] = min(ls[act], ls[succ] - self._dur[act])
        for act in self._names:
            self.slack[act] = ls[act] - es[act]
            self.earliest_start[act] = es[act]
            self.latest_start[act] = ls[act]
        return project_duration, self.slack

    def _topological_sort(self) -> List[Any]:
        in_degree = {act: len(self._preds.get(act, [])) for act in self._names}
        queue = [act for act in self._names if in_degree[act] == 0]
        result = []
        adj = self._succs
        while queue:
            node = queue.pop(0)
            result.append(node)
            for succ in adj.get(node, []):
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)
        return result

    def get_critical_path(self) -> List[Any]:
        return [act for act, _, _ in self.activities if self.slack.get(act, 0.0) == 0.0]


class Scheduler:
    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
        self.resource_capacities: Dict[str, int] = {}

    def add_task(self, task_id: Any, duration: float, resources: Dict[str, int], dependencies: List[Any] = None):
        self.tasks.append({
            "id": task_id, "duration": duration, "resources": resources,
            "dependencies": dependencies or [], "start": 0.0,
        })

    def set_capacity(self, resource: str, capacity: int):
        self.resource_capacities[resource] = capacity

    def schedule(self) -> Dict[Any, float]:
        task_map = {t["id"]: t for t in self.tasks}
        for task in self.tasks:
            if not task["dependencies"]:
                task["start"] = 0.0
            else:
                task["start"] = max(task_map[d]["start"] + task_map[d]["duration"] for d in task["dependencies"])
        schedule = {t["id"]: t["start"] for t in self.tasks}
        return schedule

    def get_makespan(self) -> float:
        if not self.tasks:
            return 0.0
        return max(t["start"] + t["duration"] for t in self.tasks)
