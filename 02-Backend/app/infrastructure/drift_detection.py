"""Drift detection for infrastructure."""

from __future__ import annotations

import logging
from typing import Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    CONFIGURATION = "configuration"
    SCALING = "scaling"
    SECURITY = "security"
    NETWORKING = "networking"
    STORAGE = "storage"


@dataclass
class DriftDetection:
    resource_id: str
    resource_type: str
    drift_type: DriftType
    expected_value: Any
    actual_value: Any
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False


class DriftDetector:
    """Detect infrastructure drift."""

    def __init__(self) -> None:
        self._detections: List[DriftDetection] = []

    def detect_drift(self, detection: DriftDetection) -> None:
        self._detections.append(detection)
        logger.warning(f"Drift detected: {detection.resource_id} ({detection.drift_type.value})")

    def get_unresolved_drifts(self) -> List[DriftDetection]:
        return [d for d in self._detections if not d.resolved]

    def get_drifts_by_type(self, drift_type: DriftType) -> List[DriftDetection]:
        return [d for d in self._detections if d.drift_type == drift_type and not d.resolved]


_drift_detector: Optional[DriftDetector] = None


def get_drift_detector() -> DriftDetector:
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = DriftDetector()
    return _drift_detector
