from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Run:
    run_id: str
    experiment_name: str
    state: str = "running"
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, list[tuple[Any, Any]]] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


class Experiment:
    def __init__(self, name: str, storage_dir: str = "experiments") -> None:
        self.name = name
        self.experiment_id = str(uuid.uuid4())
        self.storage_dir = storage_dir
        self.created_at = datetime.now(timezone.utc)
        self.runs: dict[str, Run] = {}

    def start_run(self, run_name: str = "", parameters: dict[str, Any] | None = None) -> Run:
        run_id = str(uuid.uuid4())
        run = Run(run_id=run_id, experiment_name=run_name or self.name)
        run.parameters = parameters or {}
        self.runs[run_id] = run
        return run

    def stop_run(self, run_id: str) -> None:
        run = self.runs.get(run_id)
        if run:
            run.state = "completed"
            run.end_time = datetime.now(timezone.utc)

    def log_metric(self, run_id: str, key: str, value: float, step: int | None = None) -> None:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found")
        ts = datetime.now(timezone.utc)
        if key not in run.metrics:
            run.metrics[key] = []
        run.metrics[key].append((ts, value))
        from models.llm.tracking.metrics import MetricStore
        store = MetricStore(self.storage_dir)
        store.log_scalar(run_id, key, value, ts, step)

    def log_parameters(self, run_id: str, parameters: dict[str, Any]) -> None:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found")
        run.parameters.update(parameters)

    def log_artifact(self, run_id: str, path: str, metadata: dict[str, Any] | None = None) -> None:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found")
        run.artifacts.append({"path": path, "metadata": metadata or {}, "timestamp": datetime.now(timezone.utc).isoformat()})

    def log_histogram(self, run_id: str, key: str, values: list[float]) -> None:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found")
        if key not in run.metrics:
            run.metrics[key] = []
        run.metrics[key].append(("histogram", values))
        from models.llm.tracking.metrics import MetricStore
        store = MetricStore(self.storage_dir)
        store.log_histogram(run_id, key, values)

    def log_image(self, run_id: str, key: str, image_path: str) -> None:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError(f"Run {run_id} not found")
        if key not in run.metrics:
            run.metrics[key] = []
        run.metrics[key].append(("image", image_path))
        from models.llm.tracking.metrics import MetricStore
        store = MetricStore(self.storage_dir)
        store.log_image(run_id, key, image_path)

    def compare_runs(self, run_ids: list[str], metric_keys: list[str] | None = None) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for run_id in run_ids:
            run = self.runs.get(run_id)
            if not run:
                continue
            from models.llm.tracking.metrics import MetricStore
            store = MetricStore(self.storage_dir)
            run_metrics: dict[str, Any] = {}
            if metric_keys:
                for k in metric_keys:
                    if k in run.metrics:
                        run_metrics[k] = store.aggregate(run_id, k)
            else:
                for k in run.metrics:
                    run_metrics[k] = store.aggregate(run_id, k)
            results[run_id] = {
                "run_id": run.run_id,
                "state": run.state,
                "duration_seconds": (run.end_time - run.start_time).total_seconds() if run.end_time else None,
                "parameters": run.parameters,
                "metrics": run_metrics,
            }
        return results

    def get_best_run(self, metric: str, mode: str = "min") -> Run | None:
        scored: list[tuple[float, Run]] = []
        for run in self.runs.values():
            if run.state != "completed":
                continue
            from models.llm.tracking.metrics import MetricStore
            store = MetricStore(self.storage_dir)
            agg = store.aggregate(run.run_id, metric)
            if agg is None:
                continue
            scored.append((agg["mean"], run))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=(mode == "max"))
        return scored[0][1]
