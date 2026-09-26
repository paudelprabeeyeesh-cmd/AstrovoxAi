"""Data quality validation and profiling."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    dataset_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    null_counts: Dict[str, int]
    issues: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataQualityValidator:
    def __init__(self) -> None:
        self._checks: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

    def register_check(self, name: str, check: Callable[[Dict[str, Any]], bool]) -> None:
        self._checks[name] = check

    def validate_dataset(self, dataset: List[Dict[str, Any]]) -> QualityReport:
        total = len(dataset)
        valid = 0
        invalid = 0
        null_counts: Dict[str, int] = {}
        issues: List[str] = []
        for record in dataset:
            record_issues = []
            for key, value in record.items():
                if value is None:
                    null_counts[key] = null_counts.get(key, 0) + 1
                    record_issues.append(f"null in column {key}")
            for name, check in self._checks.items():
                if not check(record):
                    record_issues.append(f"failed check {name}")
            if record_issues:
                invalid += 1
                issues.extend(record_issues)
            else:
                valid += 1
        return QualityReport(
            dataset_name="unnamed",
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            duplicate_records=0,
            null_counts=null_counts,
            issues=issues,
        )


data_quality_validator = DataQualityValidator()
