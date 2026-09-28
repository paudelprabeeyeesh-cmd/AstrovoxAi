from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class MetricRecord:
    run_id: str
    key: str
    step: int | None
    timestamp: datetime
    value: Any
    metric_type: str = "scalar"


class MetricStore:
    def __init__(self, storage_dir: str = "experiments") -> None:
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._metrics: list[MetricRecord] = []
        self._load()

    def _file_path(self) -> str:
        return os.path.join(self.storage_dir, "metrics.jsonl")

    def _load(self) -> None:
        if not os.path.exists(self._file_path()):
            return
        with open(self._file_path(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                self._metrics.append(MetricRecord(**data))

    def _persist(self, record: MetricRecord) -> None:
        with open(self._file_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "run_id": record.run_id,
                "key": record.key,
                "step": record.step,
                "timestamp": record.timestamp.isoformat(),
                "value": record.value,
                "metric_type": record.metric_type,
            }) + "\n")

    def log_scalar(self, run_id: str, key: str, value: float, timestamp: datetime | None = None, step: int | None = None) -> None:
        record = MetricRecord(run_id=run_id, key=key, step=step, timestamp=timestamp or datetime.now(timezone.utc), value=value, metric_type="scalar")
        self._metrics.append(record)
        self._persist(record)

    def log_histogram(self, run_id: str, key: str, values: list[float], timestamp: datetime | None = None) -> None:
        record = MetricRecord(run_id=run_id, key=key, step=None, timestamp=timestamp or datetime.now(timezone.utc), value=values, metric_type="histogram")
        self._metrics.append(record)
        self._persist(record)

    def log_image(self, run_id: str, key: str, image_path: str, timestamp: datetime | None = None) -> None:
        record = MetricRecord(run_id=run_id, key=key, step=None, timestamp=timestamp or datetime.now(timezone.utc), value=image_path, metric_type="image")
        self._metrics.append(record)
        self._persist(record)

    def get(self, run_id: str, key: str) -> list[MetricRecord]:
        return [m for m in self._metrics if m.run_id == run_id and m.key == key]

    def aggregate(self, run_id: str, key: str) -> dict[str, Any] | None:
        records = self.get(run_id, key)
        if not records:
            return None
        scalar_records = [r for r in records if r.metric_type == "scalar"]
        if scalar_records:
            values = [r.value for r in scalar_records]
            return {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "last": values[-1],
                "count": len(values),
            }
        return {"type": records[0].metric_type, "count": len(records)}

    def get_all_run_ids(self) -> list[str]:
        return list({m.run_id for m in self._metrics})
