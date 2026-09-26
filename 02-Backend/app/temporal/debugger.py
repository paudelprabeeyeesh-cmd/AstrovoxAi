"""High-level TimeTravelDebugger facade.

Provides:
- TimeTravelDebugger - reverse debugging
- TimeSlice - state snapshot
- DebuggerAPI - for time-travel
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TimeSlice:
    """State snapshot at a point in time."""

    slice_id: str
    timestamp: datetime
    version: int
    event_position: int
    state: Dict[str, Any]
    event: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "event_position": self.event_position,
            "state": self.state,
            "event": self.event,
            "metadata": self.metadata,
        }


@dataclass
class DebuggerAPI:
    """Time-travel API for the debugger."""

    event_store: Any
    snapshot_engine: Any

    def time_travel(self, aggregate_id: str, version: int, direction: str = "forward") -> Dict[str, Any]:
        return {"aggregate_id": aggregate_id, "version": version, "direction": direction}

    def reverse_time(self, aggregate_id: str, steps: int = 1) -> Dict[str, Any]:
        return {"aggregate_id": aggregate_id, "steps": steps, "direction": "reverse"}


class TimeTravelDebugger:
    """Time-travel debugger."""

    def __init__(self, event_store: Any, snapshot_engine: Any) -> None:
        self.event_store = event_store
        self.snapshot_engine = snapshot_engine
        self._lock = False

    def time_travel(
        self,
        aggregate_id: str,
        version: int,
        action: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {"aggregate_id": aggregate_id, "version": version, "action": action or "unknown"}

    def reverse_time(self, aggregate_id: str, steps: int = 1) -> Dict[str, Any]:
        return {"aggregate_id": aggregate_id, "steps": steps, "direction": "reverse"}
