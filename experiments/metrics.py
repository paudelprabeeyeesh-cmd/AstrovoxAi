import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MetricLogger:
    def __init__(self, experiment_id: str, log_dir: Optional[Path] = None):
        self.experiment_id = experiment_id
        self._metrics: List[Dict[str, Any]] = []
        self._log_dir = log_dir or Path(__file__).resolve().parent.parent.parent / "experiments" / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._csv_path = self._log_dir / f"{experiment_id}_metrics.csv"
        self._init_csv()

    def _init_csv(self) -> None:
        if not self._csv_path.exists():
            with open(self._csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "step", "name", "value"])

    def log_metric(self, name: str, value: float, step: int, timestamp: Optional[str] = None) -> None:
        ts = timestamp or datetime.utcnow().isoformat() + "Z"
        record = {"timestamp": ts, "step": step, "name": name, "value": value}
        self._metrics.append(record)
        with open(self._csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([ts, step, name, value])

    def log_metrics(self, metrics: Dict[str, float], step: int, timestamp: Optional[str] = None) -> None:
        for name, value in metrics.items():
            self.log_metric(name, value, step, timestamp)

    def get_metric(self, name: str) -> List[Dict[str, Any]]:
        return [m for m in self._metrics if m["name"] == name]

    def get_latest(self, name: str) -> Optional[Dict[str, Any]]:
        matches = self.get_metric(name)
        return matches[-1] if matches else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "metrics": self._metrics,
            "csv_path": str(self._csv_path),
        }

    def save(self) -> Path:
        path = self._log_dir / f"{self.experiment_id}_metrics.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        return path
