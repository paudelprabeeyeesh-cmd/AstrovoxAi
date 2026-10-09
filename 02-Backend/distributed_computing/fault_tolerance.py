import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff: float = 1.0
    _attempts: int = field(default=0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exc: Optional[Exception] = None
        for _ in range(self.max_retries):
            try:
                with self._lock:
                    self._attempts += 1
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                time.sleep(self.backoff)
        raise last_exc  # type: ignore

    def reset(self) -> None:
        with self._lock:
            self._attempts = 0

    def attempts(self) -> int:
        with self._lock:
            return self._attempts


@dataclass
class HeartbeatMonitor:
    node_id: str
    interval: float = 1.0
    timeout: float = 3.0
    _last_heartbeat: float = field(default_factory=time.time, init=False, repr=False)
    _alive: bool = field(default=True, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def pulse(self) -> None:
        with self._lock:
            self._last_heartbeat = time.time()
            self._alive = True

    def check(self) -> bool:
        with self._lock:
            if time.time() - self._last_heartbeat > self.timeout:
                self._alive = False
            return self._alive

    def start_monitoring(self, callback: Callable[[str], None]) -> None:
        def _monitor() -> None:
            while True:
                time.sleep(self.interval)
                if not self.check():
                    callback(self.node_id)

        t = threading.Thread(target=_monitor, daemon=True)
        t.start()


class FailureDetector:
    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout
        self._monitors: Dict[str, HeartbeatMonitor] = {}
        self._dead: List[str] = []
        self._lock = threading.Lock()

    def register(self, node_id: str, callback: Callable[[str], None]) -> None:
        monitor = HeartbeatMonitor(node_id=node_id, timeout=self.timeout)
        monitor.start_monitoring(callback)
        with self._lock:
            self._monitors[node_id] = monitor

    def pulse(self, node_id: str) -> None:
        with self._lock:
            monitor = self._monitors.get(node_id)
        if monitor:
            monitor.pulse()

    def dead_nodes(self) -> List[str]:
        with self._lock:
            return list(self._dead)
