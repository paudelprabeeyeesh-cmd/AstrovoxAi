"""Replay engine for event-sourced systems.

Implements:
- Deterministic replay from event store
- Time-travel debugging
- Point-in-time recovery
- Conditional replay (by event type, aggregate, time range)
- Replay verification
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .event_store import EventEnvelope, EventStore

logger = logging.getLogger(__name__)


@dataclass
class ReplayOptions:
    """Options for event replay."""

    event_type: Optional[str] = None
    aggregate_id: Optional[str] = None
    since_position: int = 0
    until_position: Optional[int] = None
    since_timestamp: Optional[datetime] = None
    until_timestamp: Optional[datetime] = None
    max_events: int = 100_000
    verify: bool = False  # Verify replay produces same result
    dry_run: bool = False


class ReplayEngine:
    """Replays events from event store with various strategies.

    Features:
    - Full replay from beginning
    - Incremental replay from checkpoint
    - Point-in-time replay
    - Time-travel debugging
    - Replay verification
    """

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store
        self._replay_handlers: List[Callable[[EventEnvelope], None]] = []
        self._verification_handlers: List[Callable[[EventEnvelope], None]] = []

    def replay(self, options: ReplayOptions) -> ReplayResult:
        """Replay events matching options."""
        start = time.monotonic()
        events = self._filter_events(options)

        if options.dry_run:
            return ReplayResult(
                events_matched=len(events),
                events_processed=0,
                duration_ms=(time.monotonic() - start) * 1000,
                dry_run=True,
            )

        processed = 0
        errors = []

        for event in events:
            try:
                for handler in self._replay_handlers:
                    handler(event)
                processed += 1
            except Exception as e:
                errors.append({
                    "event_id": event.event_id,
                    "error": str(e),
                })
                logger.error("replay failed on event %s: %s", event.event_id, e)

        duration_ms = (time.monotonic() - start) * 1000
        return ReplayResult(
            events_matched=len(events),
            events_processed=processed,
            errors=errors,
            duration_ms=duration_ms,
        )

    def _filter_events(self, options: ReplayOptions) -> List[EventEnvelope]:
        """Filter events based on replay options."""
        events = self._store.get_events(
            event_type=options.event_type,
            since_position=options.since_position,
            limit=options.max_events,
        )

        # Filter by aggregate_id
        if options.aggregate_id:
            events = [e for e in events if e.payload.get("aggregate_id") == options.aggregate_id]

        # Filter by time range
        if options.since_timestamp:
            events = [e for e in events if e.occurred_at >= options.since_timestamp]
        if options.until_timestamp:
            events = [e for e in events if e.occurred_at <= options.until_timestamp]

        # Filter by position
        if options.until_position:
            events = [e for e in events if e._position <= options.until_position]

        return events

    def replay_from_position(self, position: int, handler: Callable[[EventEnvelope], None]) -> int:
        """Replay events from a specific position."""
        events = self._store.get_events(since_position=position)
        count = 0
        for event in events:
            try:
                handler(event)
                count += 1
            except Exception:
                logger.exception("replay handler failed at position %d", position)
                break
        return count

    def replay_to_point_in_time(self, target_time: datetime, handler: Callable[[EventEnvelope], None]) -> int:
        """Replay events up to a specific point in time."""
        options = ReplayOptions(
            until_timestamp=target_time,
            max_events=100_000,
        )
        result = self.replay(options)
        return result.events_processed

    def verify_replay(self, handler: Callable[[EventEnvelope], None], expected_state: Dict[str, Any]) -> bool:
        """Verify that replay produces expected state."""
        state: Dict[str, Any] = {}
        options = ReplayOptions(max_events=100_000)

        for event in self._filter_events(options):
            try:
                handler(event, state)
            except Exception:
                logger.exception("verification replay failed")
                return False

        return state == expected_state

    def add_handler(self, handler: Callable[[EventEnvelope], None]) -> None:
        """Add a replay handler."""
        self._replay_handlers.append(handler)

    def add_verification_handler(self, handler: Callable[[EventEnvelope], None]) -> None:
        """Add a verification handler."""
        self._verification_handlers.append(handler)


@dataclass
class ReplayResult:
    """Result of a replay operation."""

    events_matched: int
    events_processed: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    dry_run: bool = False
