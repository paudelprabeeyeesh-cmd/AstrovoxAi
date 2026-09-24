import threading
from typing import Any, Callable, Dict, List, Optional


class EventProcessor:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._middlewares: List[Callable] = []
        self._lock = threading.Lock()

    def add_handler(self, event_type: str, handler: Callable[[dict], Any]) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def add_middleware(self, middleware: Callable[[dict], Optional[dict]]) -> None:
        with self._lock:
            self._middlewares.append(middleware)

    def process(self, event: dict) -> List[Any]:
        with self._lock:
            handlers = list(self._handlers.get(event.get("type", ""), []))
            middlewares = list(self._middlewares)

        current = dict(event)
        for middleware in middlewares:
            result = middleware(current)
            if result is None:
                return []
            current = result

        results = []
        for handler in handlers:
            result = handler(current)
            if result is not None:
                results.append(result)
        return results

    def process_batch(self, events: List[dict]) -> List[Any]:
        results = []
        for event in events:
            results.extend(self.process(event))
        return results

    def handlers_for(self, event_type: str) -> List[Callable]:
        with self._lock:
            return list(self._handlers.get(event_type, []))
