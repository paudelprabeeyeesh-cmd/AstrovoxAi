"""Time-travel query API.

Provides:
- Point-in-time state queries
- Event-based state queries
- Snapshot-based queries
- Range queries
- Time-travel query results
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryMode(Enum):
    """Point-in-time query mode."""

    SNAPSHOT = "snapshot"
    EVENT_REPLAY = "event_replay"
    HYBRID = "hybrid"


class TimeRangeOperator(Enum):
    """Time range operators."""

    BEFORE = "before"
    AFTER = "after"
    BETWEEN = "between"
    AT = "at"


@dataclass
class PointInTimeQuery:
    """Query for state at specific point in time."""

    query_id: str
    aggregate_id: str
    timestamp: Optional[datetime] = None
    version: Optional[int] = None
    event_position: Optional[int] = None
    mode: QueryMode = QueryMode.HYBRID
    parameters: Dict[str, Any] = field(default_factory=dict)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TimeRangeQuery:
    """Query for state over time range."""

    query_id: str
    aggregate_id: str
    start: datetime
    end: datetime
    operator: TimeRangeOperator = TimeRangeOperator.BETWEEN
    parameters: Dict[str, Any] = field(default_factory=dict)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TimeTravelResult:
    """Result of time-travel query."""

    query_id: str
    aggregate_id: str
    timestamp: datetime
    version: int
    state: Dict[str, Any]
    source: str = "snapshot"
    cache_hit: bool = False
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "state": self.state,
            "source": self.source,
            "cache_hit": self.cache_hit,
            "issued_at": self.issued_at.isoformat(),
        }


class TimeTravelAPI:
    """Time-travel query API.

    Provides:
    - Point-in-time state queries
    - Event-based state queries
    - Snapshot-based queries
    - Range queries
    - Cache invalidation
    """

    def __init__(self, event_store: Any, snapshot_engine: Any) -> None:
        self.event_store = event_store
        self.snapshot_engine = snapshot_engine
        self._cache: Dict[str, TimeTravelResult] = {}
        self._lock = False

    async def query(self, pit_query: PointInTimeQuery) -> TimeTravelResult:
        """Execute point-in-time query."""
        cache_key = f"{pit_query.aggregate_id}:{pit_query.version}:{pit_query.timestamp}:{pit_query.event_position}"
        if cache_key in self._cache:
            result = self._cache[cache_key]
            result.cache_hit = True
            return result

        state = None
        source = "unknown"
        version = pit_query.version or 0
        timestamp = pit_query.timestamp or datetime.now(timezone.utc)

        if pit_query.mode == QueryMode.SNAPSHOT or pit_query.mode == QueryMode.HYBRID:
            if pit_query.version is not None:
                state_point = self.snapshot_engine.get_state_at_version(pit_query.aggregate_id, pit_query.version)
            elif pit_query.timestamp is not None:
                state_point = self.snapshot_engine.get_state_at_timestamp(pit_query.aggregate_id, pit_query.timestamp)
            elif pit_query.event_position is not None:
                state_point = self.snapshot_engine.get_state_at_event_position(pit_query.aggregate_id, pit_query.event_position)
            else:
                state_point = None

            if state_point:
                state = copy.deepcopy(state_point.state)
                version = state_point.version
                timestamp = state_point.timestamp
                source = "snapshot"

        if state is None and pit_query.mode != QueryMode.SNAPSHOT:
            state = await self._replay_state(pit_query)
            source = "event_replay"

        if state is None:
            state = self._empty_state(pit_query.aggregate_id)
            version = version or 0
            timestamp = timestamp or datetime.now(timezone.utc)
            source = "empty"

        result = TimeTravelResult(
            query_id=pit_query.query_id,
            aggregate_id=pit_query.aggregate_id,
            timestamp=timestamp,
            version=version,
            state=state,
            source=source,
        )
        self._cache[cache_key] = result
        return result

    async def _replay_state(self, pit_query: PointInTimeQuery) -> Optional[Dict[str, Any]]:
        if self.event_store is None:
            return None
        state: Dict[str, Any] = {}
        if pit_query.version:
            events = self.event_store.get_events(aggregate_id=pit_query.aggregate_id, limit=pit_query.version)
        elif pit_query.event_position:
            events = self.event_store.get_events(aggregate_id=pit_query.aggregate_id, limit=pit_query.event_position)
        else:
            return None
        for event in events:
            if hasattr(event, "payload"):
                state = self._apply_state(state, event.payload)
        return state

    def _apply_state(self, state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        return {**state, **payload}

    def _empty_state(self, aggregate_id: str) -> Dict[str, Any]:
        return {"aggregate_id": aggregate_id}

    async def query_range(self, time_range: TimeRangeQuery) -> List[TimeTravelResult]:
        if self.snapshot_engine is None:
            return []
        state_points = self.snapshot_engine.get_state_points(time_range.aggregate_id)
        results = []
        for sp in state_points:
            if time_range.operator == TimeRangeOperator.BEFORE:
                if sp.timestamp < time_range.start:
                    results.append(self._state_point_to_result(sp))
            elif time_range.operator == TimeRangeOperator.AFTER:
                if sp.timestamp > time_range.end:
                    results.append(self._state_point_to_result(sp))
            elif time_range.operator == TimeRangeOperator.BETWEEN:
                if time_range.start <= sp.timestamp <= time_range.end:
                    results.append(self._state_point_to_result(sp))
            elif time_range.operator == TimeRangeOperator.AT:
                if time_range.start <= sp.timestamp <= time_range.end:
                    results.append(self._state_point_to_result(sp))
        return results

    def _state_point_to_result(self, state_point: Any) -> TimeTravelResult:
        return TimeTravelResult(
            query_id="",
            aggregate_id=state_point.aggregate_id,
            timestamp=state_point.timestamp,
            version=state_point.version,
            state=state_point.state,
            source="state_point",
        )

    def invalidate_cache(self, aggregate_id: Optional[str] = None) -> None:
        if aggregate_id is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if not k.startswith(aggregate_id)}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self._cache),
            "event_store": self.event_store is not None,
            "snapshot_engine": self.snapshot_engine is not None,
        }
