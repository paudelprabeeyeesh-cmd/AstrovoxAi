import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExperimentLogger:
    def __init__(self, log_dir: str = "experiments"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._file = open(os.path.join(log_dir, f"{self.experiment_id}.jsonl"), "a", encoding="utf-8")
        self.metrics = {}

    def log_config(self, config: Dict[str, Any]):
        self._file.write(json.dumps({"type": "config", "data": config}) + "\n")
        self._file.flush()

    def log_metrics(self, metrics: Dict[str, Any], step: int):
        record = {"type": "metrics", "step": step, "data": metrics}
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()
        self.metrics[step] = metrics

    def log_artifact(self, path: str, metadata: Optional[Dict] = None):
        record = {"type": "artifact", "path": path, "metadata": metadata or {}}
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-dir", default="experiments")
    args = parser.parse_args()
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    tracker = ExperimentLogger(args.log_dir)
    try:
        import sys
        for line in sys.stdin:
            record = json.loads(line)
            if record.get("type") == "metrics":
                tracker.log_metrics(record["data"], record.get("step", 0))
    except KeyboardInterrupt:
        pass
    finally:
        tracker.close()


if __name__ == "__main__":
    main()
