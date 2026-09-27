import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "experiments"
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


class ExperimentTracker:
    def __init__(self, experiment_id: str, name: str):
        self.experiment_id = experiment_id
        self.name = name
        self._params: Dict[str, Any] = {}
        self._metrics: List[Dict[str, Any]] = []
        self._artifacts: List[Dict[str, Any]] = []
        self._start_time = datetime.utcnow().isoformat() + "Z"
        self._end_time: Optional[str] = None
        self._status = "running"

    def log_params(self, params: Dict[str, Any]) -> None:
        self._params.update(params)

    def log_metric(self, name: str, value: float, step: int, timestamp: Optional[str] = None) -> None:
        self._metrics.append({
            "name": name,
            "value": value,
            "step": step,
            "timestamp": timestamp or datetime.utcnow().isoformat() + "Z",
        })

    def log_artifact(self, name: str, path: str, artifact_type: str = "file") -> None:
        self._artifacts.append({
            "name": name,
            "path": path,
            "type": artifact_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def set_status(self, status: str) -> None:
        self._status = status
        if status in ("completed", "failed", "killed"):
            self._end_time = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self._status,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "params": self._params,
            "metrics": self._metrics,
            "artifacts": self._artifacts,
        }

    def save(self) -> Path:
        path = EXPERIMENTS_DIR / f"{self.experiment_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        return path

    @classmethod
    def load(cls, experiment_id: str) -> "ExperimentTracker":
        path = EXPERIMENTS_DIR / f"{experiment_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Experiment not found: {experiment_id}")
        data = json.loads(path.read_text())
        tracker = cls(data["experiment_id"], data["name"])
        tracker._params = data.get("params", {})
        tracker._metrics = data.get("metrics", [])
        tracker._artifacts = data.get("artifacts", [])
        tracker._start_time = data.get("start_time")
        tracker._end_time = data.get("end_time")
        tracker._status = data.get("status", "unknown")
        return tracker
