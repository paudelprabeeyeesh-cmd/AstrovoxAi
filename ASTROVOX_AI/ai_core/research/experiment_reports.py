import logging
from dataclasses import dataclass
from typing import List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ExperimentRecord:
    experiment_id: str
    model: str
    dataset: str
    metrics: dict
    timestamp: str
    notes: Optional[str] = None


class ExperimentReporter:
    def __init__(self):
        self.records: List[ExperimentRecord] = []

    def add_record(self, record: ExperimentRecord) -> None:
        self.records.append(record)
        logger.info("Recorded experiment %s", record.experiment_id)

    def publish(self) -> str:
        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "experiments": [
                {
                    "experiment_id": r.experiment_id,
                    "model": r.model,
                    "dataset": r.dataset,
                    "metrics": r.metrics,
                    "timestamp": r.timestamp,
                    "notes": r.notes,
                }
                for r in self.records
            ],
        }
        payload = json.dumps(report, indent=2)
        logger.info("Published %d experiment reports", len(self.records))
        return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reporter = ExperimentReporter()
    reporter.add_record(ExperimentRecord(
        experiment_id="exp-001",
        model="transformer",
        dataset="synthetic",
        metrics={"accuracy": 0.9, "latency_ms": 12.5},
        timestamp=datetime.utcnow().isoformat() + "Z",
        notes="baseline",
    ))
    print(reporter.publish())
