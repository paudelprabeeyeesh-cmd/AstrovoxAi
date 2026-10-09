import threading
import time


class EventTracker:
    def __init__(self):
        self._events = []
        self._lock = threading.Lock()

    def track(self, event_type: str, payload: dict = None) -> dict:
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "payload": payload or {},
        }
        with self._lock:
            self._events.append(event)
        return event

    def get_events(
        self,
        event_type: str = None,
        since: float = None,
        until: float = None,
    ):
        with self._lock:
            events = list(self._events)
        result = []
        for event in events:
            ts = event["timestamp"]
            if event_type is not None and event["type"] != event_type:
                continue
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
            result.append(event)
        return result

    def count(self, event_type: str = None) -> int:
        return len(self.get_events(event_type=event_type))

    def clear(self):
        with self._lock:
            self._events.clear()
