from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(order=True)
class Interval:
    start: float
    end: float
    label: str = ""

    def __post_init__(self):
        if self.end < self.start:
            raise ValueError("Interval end must be >= start")

    def length(self) -> float:
        return self.end - self.start

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and self.end > other.start

    def contains(self, other: "Interval") -> bool:
        return self.start <= other.start and self.end >= other.end

    def meets(self, other: "Interval") -> bool:
        return abs(self.end - other.start) <= 1e-9

    def before(self, other: "Interval") -> bool:
        return self.end <= other.start

    def after(self, other: "Interval") -> bool:
        return self.start >= other.end

    def equals(self, other: "Interval") -> bool:
        return abs(self.start - other.start) <= 1e-9 and abs(self.end - other.end) <= 1e-9


class IntervalReasoner:
    def __init__(self):
        self.intervals: Dict[str, Interval] = {}
        self._counter = 0

    def add_interval(self, start: float, end: float, label: str = "") -> str:
        if end < start:
            raise ValueError("Invalid interval")
        iid = f"int_{self._counter}"
        self._counter += 1
        self.intervals[iid] = Interval(start=start, end=end, label=label)
        return iid

    def query_relations(self, iid: str) -> Dict[str, List[str]]:
        target = self.intervals.get(iid)
        if not target:
            return {}
        relations: Dict[str, List[str]] = {
            "overlaps": [],
            "contains": [],
            "contained_by": [],
            "meets": [],
            "before": [],
            "after": [],
            "equals": [],
        }
        for other_id, other in self.intervals.items():
            if other_id == iid:
                continue
            if target.equals(other):
                relations["equals"].append(other_id)
            elif target.contains(other):
                relations["contains"].append(other_id)
            elif other.contains(target):
                relations["contained_by"].append(other_id)
            elif target.overlaps(other):
                relations["overlaps"].append(other_id)
            elif target.meets(other):
                relations["meets"].append(other_id)
            elif target.before(other):
                relations["before"].append(other_id)
            elif target.after(other):
                relations["after"].append(other_id)
        return relations

    def merge_overlapping(self) -> List[Interval]:
        if not self.intervals:
            return []
        sorted_ints = sorted(self.intervals.values(), key=lambda x: (x.start, x.end))
        merged = [sorted_ints[0]]
        for current in sorted_ints[1:]:
            last = merged[-1]
            if last.overlaps(current) or last.meets(current):
                merged[-1] = Interval(start=last.start, end=max(last.end, current.end), label=last.label or current.label)
            else:
                merged.append(current)
        return merged

    def gaps(self) -> List[Tuple[float, float]]:
        merged = self.merge_overlapping()
        gaps = []
        for i in range(len(merged) - 1):
            gap_start = merged[i].end
            gap_end = merged[i + 1].start
            if gap_end > gap_start:
                gaps.append((gap_start, gap_end))
        return gaps
