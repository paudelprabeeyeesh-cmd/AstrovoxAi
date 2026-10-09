import heapq
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Window:
    start: float
    end: float
    events: List[dict] = field(default_factory=list)


class WindowAggregator:
    def __init__(self, window_size: float, slide: Optional[float] = None):
        self.window_size = window_size
        self.slide = slide if slide is not None else window_size
        self._windows: Dict[tuple, Window] = {}

    def _window_key(self, timestamp: float) -> tuple:
        start = (int(timestamp // self.slide)) * self.slide
        end = start + self.window_size
        return (start, end)

    def add_event(self, event: dict) -> Optional[Window]:
        key = self._window_key(event["timestamp"])
        if key not in self._windows:
            self._windows[key] = Window(start=key[0], end=key[1])
        self._windows[key].events.append(event)
        return self._windows[key]

    def add_events(self, events: List[dict]) -> List[Window]:
        updated = []
        for event in events:
            window = self.add_event(event)
            if window is not None:
                updated.append(window)
        return updated

    def get_window(self, timestamp: float) -> Optional[Window]:
        key = self._window_key(timestamp)
        return self._windows.get(key)

    def windows(self) -> List[Window]:
        return sorted(self._windows.values(), key=lambda w: w.start)

    def aggregate(
        self,
        agg_func: Callable[[List[dict]], Dict[str, Any]],
    ) -> Dict[tuple, Any]:
        result = {}
        for key, window in self._windows.items():
            result[key] = agg_func(window.events)
        return result

    def count_by_type(self) -> Dict[tuple, Dict[str, int]]:
        return self.aggregate(
            lambda events: {
                etype: sum(1 for e in events if e["type"] == etype)
                for etype in {e["type"] for e in events}
            }
        )

    def sum_field(self, field: str) -> Dict[tuple, Dict[str, float]]:
        def _sum(events):
            totals = defaultdict(float)
            for event in events:
                value = event.get("payload", {}).get(field)
                if value is not None:
                    try:
                        totals[event["type"]] += float(value)
                    except (TypeError, ValueError):
                        pass
            return dict(totals)

        return self.aggregate(_sum)

    def avg_field(self, field: str) -> Dict[tuple, Dict[str, float]]:
        def _avg(events):
            sums = defaultdict(float)
            counts = defaultdict(int)
            for event in events:
                value = event.get("payload", {}).get(field)
                if value is not None:
                    try:
                        sums[event["type"]] += float(value)
                        counts[event["type"]] += 1
                    except (TypeError, ValueError):
                        pass
            return {
                etype: sums[etype] / counts[etype]
                for etype in sums
                if counts[etype] > 0
            }

        return self.aggregate(_avg)

    def clear(self):
        self._windows.clear()
