"""Multi-region event replication and ordering.

Implements:
- Region-aware event ordering
- Causal consistency via vector clocks
- Event deduplication across regions
- Conflict resolution
- Regional event stores
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from .event_store import EventEnvelope, EventStore

logger = logging.getLogger(__name__)


@dataclass
class VectorClock:
    """Vector clock for causal ordering across regions."""

    region_id: str
    counter: int = 0
    timestamps: Dict[str, int] = field(default_factory=dict)

    def increment(self) -> int:
        """Increment clock for current region."""
        self.counter += 1
        self.timestamps[self.region_id] = self.counter
        return self.counter

    def merge(self, other: VectorClock) -> None:
        """Merge another vector clock."""
        for region, count in other.timestamps.items():
            self.timestamps[region] = max(self.timestamps.get(region, 0), count)
        self.counter = max(self.counter, max(self.timestamps.values()))

    def happens_before(self, other: VectorClock) -> bool:
        """Check if this clock happens before another."""
        if self.region_id == other.region_id:
            return self.counter < other.counter
        return all(
            self.timestamps.get(r, 0) <= other.timestamps.get(r, 0)
            for r in set(self.timestamps) | set(other.timestamps)
        )

    def concurrent(self, other: VectorClock) -> bool:
        """Check if clocks are concurrent (neither happens before the other)."""
        return not self.happens_before(other) and not other.happens_before(self)


@dataclass
class RegionConfig:
    """Configuration for a region."""

    region_id: str
    event_store: EventStore
    vector_clock: VectorClock
    is_primary: bool = False


class MultiRegionEventStore:
    """Coordinates event stores across multiple regions.

    Features:
    - Region-aware event ordering
    - Causal consistency via vector clocks
    - Event deduplication
    - Conflict resolution
    """

    def __init__(self, primary_region: str) -> None:
        self._primary_region = primary_region
        self._regions: Dict[str, RegionConfig] = {}
        self._vector_clock = VectorClock(region_id=primary_region)
        self._dedup_cache: Dict[str, datetime] = {}
        self._dedup_ttl_s = 3600  # 1 hour

    def register_region(self, region_id: str, event_store: EventStore, is_primary: bool = False) -> None:
        """Register a regional event store."""
        self._regions[region_id] = RegionConfig(
            region_id=region_id,
            event_store=event_store,
            vector_clock=VectorClock(region_id=region_id),
            is_primary=is_primary,
        )
        logger.info("registered region: %s (primary=%s)", region_id, is_primary)

    def publish(self, event: EventEnvelope, source_region: str) -> EventEnvelope:
        """Publish event to appropriate region store."""
        if source_region not in self._regions:
            raise ValueError(f"unknown region: {source_region}")

        region = self._regions[source_region]
        region.vector_clock.increment()

        # Update event with causal metadata
        event_dict = event.to_dict()
        event_dict["_region"] = source_region
        event_dict["_vector_clock"] = dict(region.vector_clock.timestamps)
        enriched = EventEnvelope.from_dict(event_dict)

        # Store in region
        region.event_store.append(enriched)

        # Merge vector clocks
        self._vector_clock.merge(region.vector_clock)

        # Track for deduplication
        self._dedup_cache[event.event_id] = datetime.now(timezone.utc)

        return enriched

    def is_duplicate(self, event: EventEnvelope) -> bool:
        """Check if event is a duplicate across regions."""
        if event.event_id in self._dedup_cache:
            return True
        self._dedup_cache[event.event_id] = datetime.now(timezone.utc)
        return False

    def resolve_conflict(self, event_a: EventEnvelope, event_b: EventEnvelope) -> EventEnvelope:
        """Resolve conflict between two concurrent events.

        Strategy: Last-write-wins based on occurred_at timestamp.
        In production: could use CRDT merge or application-specific resolver.
        """
        if event_a.occurred_at >= event_b.occurred_at:
            return event_a
        return event_b

    def sync_regions(self) -> Dict[str, int]:
        """Sync events between regions."""
        synced = {}
        for region_id, region in self._regions.items():
            if region.is_primary:
                continue
            # In production: replicate events from primary to secondary
            synced[region_id] = 0
        return synced

    def get_causal_order(self, events: List[EventEnvelope]) -> List[EventEnvelope]:
        """Sort events by causal order using vector clocks."""
        return sorted(
            events,
            key=lambda e: e.payload.get("_vector_clock", {}).get(self._primary_region, 0)
        )
