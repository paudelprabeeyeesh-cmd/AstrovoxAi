"""
Job scheduling with cron-like expressions and task management.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ScheduledJob:
    name: str
    cron: str
    fn: Callable[..., Any]
    params: Dict[str, Any] = field(default_factory=dict)
    last_run: Optional[str] = None
    next_run: Optional[str] = None


class Scheduler:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def schedule(self, job: ScheduledJob) -> None:
        with self._lock:
            self._jobs[job.name] = job

    def cancel(self, name: str) -> None:
        with self._lock:
            self._jobs.pop(name, None)

    def run_job(self, name: str) -> Any:
        with self._lock:
            job = self._jobs.get(name)
        if not job:
            raise KeyError(f"job not found: {name}")
        result = job.fn(**job.params)
        now = datetime.utcnow().isoformat()
        with self._lock:
            job.last_run = now
            job.next_run = now
        return result

    def list_jobs(self) -> List[str]:
        with self._lock:
            return list(self._jobs.keys())

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        while self._running:
            with self._lock:
                for job in list(self._jobs.values()):
                    if job.next_run is None or job.next_run <= datetime.utcnow().isoformat():
                        try:
                            self.run_job(job.name)
                        except Exception as _e:  # noqa: BLE001
                            continue
            threading.Event().wait(timeout=1.0)

    def stop(self) -> None:
        self._running = False
