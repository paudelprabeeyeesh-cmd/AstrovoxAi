"""Data lineage for governance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LineageTracker:
    tracker_id: str
    resource: str
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


class DataLineage:
    def __init__(self) -> None:
        self._trackers: Dict[str, LineageTracker] = {}

    def register(self, tracker: LineageTracker) -> None:
        self._trackers[tracker.tracker_id] = tracker

    def get_lineage(self, tracker_id: str) -> Optional[LineageTracker]:
        return self._trackers.get(tracker_id)


data_lineage = DataLineage()
