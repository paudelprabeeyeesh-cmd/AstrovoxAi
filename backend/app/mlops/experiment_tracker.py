"""Experiment tracking for ML training runs."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExperimentRun:
    run_id: str
    experiment_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    status: str = "running"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None


class ExperimentTracker:
    def __init__(self) -> None:
        self._runs: Dict[str, ExperimentRun] = {}

    def start_run(self, experiment_id: str, parameters: Optional[Dict[str, Any]] = None) -> ExperimentRun:
        run_id = uuid.uuid4().hex
        run = ExperimentRun(run_id=run_id, experiment_id=experiment_id, parameters=parameters or {})
        self._runs[run_id] = run
        return run

    def log_metric(self, run_id: str, key: str, value: Any) -> None:
        run = self._runs.get(run_id)
        if run:
            run.metrics[key] = value

    def log_artifact(self, run_id: str, key: str, path: str) -> None:
        run = self._runs.get(run_id)
        if run:
            run.artifacts[key] = path

    def end_run(self, run_id: str, status: str = "completed") -> None:
        run = self._runs.get(run_id)
        if run:
            run.status = status
            run.ended_at = datetime.now(timezone.utc)

    def get_run(self, run_id: str) -> Optional[ExperimentRun]:
        return self._runs.get(run_id)


experiment_tracker = ExperimentTracker()
