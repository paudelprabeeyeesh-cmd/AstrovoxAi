"""Read-only local experiment history from real training job records."""

import json
from pathlib import Path


def list_experiments(root: str | Path) -> list[dict]:
    directory = Path(root).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("experiment root must be a directory")
    experiments = []
    for job_file in directory.glob("*/job.json"):
        try:
            job_dir = job_file.parent.resolve(strict=True)
            if not job_dir.is_relative_to(directory):
                continue
            record = json.loads(job_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and record.get("job_id") and record.get("state"):
            experiments.append(record)
    return sorted(experiments, key=lambda row: row.get("start_time", ""), reverse=True)
