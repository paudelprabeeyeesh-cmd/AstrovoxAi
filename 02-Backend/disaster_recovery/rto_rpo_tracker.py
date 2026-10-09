import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecoveryEvent:
    event_name: str
    start_time: float
    end_time: Optional[float] = None
    recovery_points: List[float] = field(default_factory=list)


class RtoRpoTracker:
    def __init__(self) -> None:
        self._events: Dict[str, RecoveryEvent] = {}
        self._lock = False

    def start_event(self, event_name: str) -> None:
        if self._lock:
            raise RuntimeError("Event already in progress")
        self._lock = True
        self._events[event_name] = RecoveryEvent(event_name=event_name, start_time=time.time())

    def end_event(self, event_name: str) -> Optional[float]:
        event = self._events.get(event_name)
        if event is None or event.end_time is not None:
            return None
        event.end_time = time.time()
        self._lock = False
        return event.end_time - event.start_time

    def record_recovery_point(self, event_name: str, timestamp: float) -> None:
        event = self._events.get(event_name)
        if event is not None and event.end_time is None:
            event.recovery_points.append(timestamp)

    def get_rto(self, event_name: str) -> Optional[float]:
        event = self._events.get(event_name)
        if event is None or event.end_time is None:
            return None
        return event.end_time - event.start_time

    def get_rpo(self, event_name: str) -> Optional[float]:
        event = self._events.get(event_name)
        if event is None or event.end_time is None or not event.recovery_points:
            return None
        return event.end_time - max(event.recovery_points)

    def get_metrics(self) -> Dict[str, Any]:
        rtos: List[float] = []
        rpos: List[float] = []
        for event in self._events.values():
            rto = self.get_rto(event.event_name)
            rpo = self.get_rpo(event.event_name)
            if rto is not None:
                rtos.append(rto)
            if rpo is not None:
                rpos.append(rpo)
        return {
            "count": len(self._events),
            "avg_rto": statistics.mean(rtos) if rtos else None,
            "max_rto": max(rtos) if rtos else None,
            "avg_rpo": statistics.mean(rpos) if rpos else None,
            "max_rpo": max(rpos) if rpos else None,
        }
