"""Projection engine for building read models from events.

Implements:
- Incremental projection updates
- Projection rebuilding from event store
- Checkpoint-based recovery
- Multi-projection coordination
- Dead-letter handling
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .event_store import EventEnvelope, EventStore

logger = logging.getLogger(__name__)


@dataclass
class ProjectionDefinition:
    """Definition of an event projection."""

    name: str
    event_types: List[str]
    handler: Callable[[EventEnvelope, Dict[str, Any]], None]
    initial_state: Dict[str, Any] = field(default_factory=dict)
    checkpoint_interval: int = 1000  # Checkpoint every N events
    max_retries: int = 3
    enabled: bool = True


@dataclass
class ProjectionCheckpoint:
    """Checkpoint for projection recovery."""

    projection_name: str
    last_position: int
    state: Dict[str, Any]
    updated_at: datetime
    retry_count: int = 0


class ProjectionEngine:
    """Manages event projections for building read models.

    Features:
    - Incremental projection updates
    - Automatic checkpointing
    - Recovery from checkpoints
    - Dead-letter handling
    """

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store
        self._projections: Dict[str, ProjectionDefinition] = {}
        self._checkpoints: Dict[str, ProjectionCheckpoint] = {}
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def register(self, projection: ProjectionDefinition) -> None:
        """Register a new projection."""
        with self._lock:
            self._projections[projection.name] = projection
            logger.info("registered projection: %s", projection.name)

    def start(self) -> None:
        """Start projection engine."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._worker_thread.start()
        logger.info("projection engine started")

    def stop(self) -> None:
        """Stop projection engine."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        logger.info("projection engine stopped")

    def _run_loop(self) -> None:
        """Main projection loop."""
        while self._running:
            try:
                for name, projection in self._projections.items():
                    if not projection.enabled:
                        continue
                    self._process_projection(name, projection)
                time.sleep(0.1)
            except Exception:
                logger.exception("error in projection loop")

    def _process_projection(self, name: str, projection: ProjectionDefinition) -> None:
        """Process events for a single projection."""
        checkpoint = self._checkpoints.get(name)
        start_position = checkpoint.last_position if checkpoint else 0

        events = self._store.get_events(
            event_type=projection.event_types[0] if projection.event_types else None,
            since_position=start_position,
            limit=projection.checkpoint_interval,
        )

        if not events:
            return

        state = checkpoint.state if checkpoint else dict(projection.initial_state)
        processed = 0

        for event in events:
            try:
                projection.handler(event, state)
                processed += 1
            except Exception as e:
                logger.error("projection %s failed on event %s: %s", name, event.event_id, e)
                self._store._dead_letter.append(event)

        # Update checkpoint
        if processed > 0:
            last_event_id = events[-1].event_id
            last_position = self._store._positions.get(last_event_id, 0)
            self._checkpoints[name] = ProjectionCheckpoint(
                projection_name=name,
                last_position=last_position,
                state=state,
                updated_at=datetime.now(timezone.utc),
            )

    def rebuild_all(self) -> Dict[str, int]:
        """Rebuild all projections from scratch."""
        results = {}
        for name, projection in self._projections.items():
            if not projection.enabled:
                continue
            count = self._store.rebuild_projection(
                name,
                lambda event, state=dict(projection.initial_state): projection.handler(event, state),
            )
            results[name] = count
            # Reset checkpoint
            self._checkpoints[name] = ProjectionCheckpoint(
                projection_name=name,
                last_position=self._store.get_position(),
                state=dict(projection.initial_state),
                updated_at=datetime.now(timezone.utc),
            )
        return results

    def get_checkpoint(self, projection_name: str) -> Optional[ProjectionCheckpoint]:
        """Get projection checkpoint."""
        return self._checkpoints.get(projection_name)

    def get_projection_state(self, projection_name: str) -> Optional[Dict[str, Any]]:
        """Get current projection state."""
        checkpoint = self._checkpoints.get(projection_name)
        return checkpoint.state if checkpoint else None
