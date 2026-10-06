"""Experiment tracking for Astrovox."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ExperimentRun:
    """A single experiment run."""
    id: str
    name: str
    config: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    started: float = field(default_factory=lambda: time.time())
    completed: float = 0.0
    status: str = "running"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "config": self.config,
                "metrics": self.metrics, "status": self.status, "started": self.started,
                "completed": self.completed}


class ExperimentTracker:
    """Track and compare experiments."""

    def __init__(self):
        self.experiments: dict[str, ExperimentRun] = {}
        self._counter = 0

    def create(self, name: str, config: dict | None = None) -> ExperimentRun:
        self._counter += 1
        run = ExperimentRun(id=f"exp_{self._counter}", name=name,
                            config=dict(config) if config else {})
        self.experiments[run.id] = run
        return run

    def log_metric(self, run_id: str, name: str, value: float) -> None:
        run = self.experiments.get(run_id)
        if run is None:
            return
        run.metrics[name] = value

    def complete(self, run_id: str) -> ExperimentRun | None:
        run = self.experiments.get(run_id)
        if run is None:
            return None
        run.completed = time.time()
        run.status = "completed"
        return run

    def get(self, run_id: str) -> ExperimentRun | None:
        return self.experiments.get(run_id)

    def list_runs(self, status: str | None = None) -> list[ExperimentRun]:
        if status is None:
            return list(self.experiments.values())
        return [r for r in self.experiments.values() if r.status == status]

    def compare(self, run_ids: list[str]) -> list[ExperimentRun]:
        return [self.experiments.get(rid) for rid in run_ids if rid in self.experiments]
