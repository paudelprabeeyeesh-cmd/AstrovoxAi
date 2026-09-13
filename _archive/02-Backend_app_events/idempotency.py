"""Idempotency tracking for event processing.

Implements:
- Idempotency key storage and checking
- Duplicate detection
- Exactly-once processing semantics
- Idempotency window management
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IdempotencyRecord:
    """Record of processed idempotency key."""

    key: str
    event_id: str
    processed_at: datetime
    result: str  # "success" | "failed"
    ttl_s: int = 86400  # 24 hours


class IdempotencyTracker:
    """Tracks processed events for exactly-once semantics.

    Features:
    - Idempotency key storage
    - TTL-based expiration
    - Duplicate detection
    - Processing result tracking
    """

    def __init__(self, default_ttl_s: int = 86400) -> None:
        self._records: Dict[str, IdempotencyRecord] = {}
        self._default_ttl = default_ttl_s
        self._lock = False

    def is_processed(self, key: str) -> bool:
        """Check if event with idempotency key was already processed."""
        self._cleanup_expired()
        return key in self._records

    def record(self, key: str, event_id: str, result: str = "success", ttl_s: Optional[int] = None) -> None:
        """Record processed event."""
        if self._lock:
            return
        self._lock = True
        try:
            ttl = ttl_s or self._default_ttl
            self._records[key] = IdempotencyRecord(
                key=key,
                event_id=event_id,
                processed_at=datetime.now(timezone.utc),
                result=result,
                ttl_s=ttl,
            )
        finally:
            self._lock = False

    def get_result(self, key: str) -> Optional[str]:
        """Get processing result for idempotency key."""
        self._cleanup_expired()
        record = self._records.get(key)
        return record.result if record else None

    def _cleanup_expired(self) -> None:
        """Remove expired records."""
        now = datetime.now(timezone.utc)
        expired = [
            key for key, record in self._records.items()
            if (now - record.processed_at).total_seconds() > record.ttl_s
        ]
        for key in expired:
            del self._records[key]

    def stats(self) -> Dict[str, Any]:
        """Get idempotency tracker statistics."""
        now = datetime.now(timezone.utc)
        active = sum(
            1 for r in self._records.values()
            if (now - r.processed_at).total_seconds() <= r.ttl_s
        )
        return {
            "total_records": len(self._records),
            "active_records": active,
            "expired_records": len(self._records) - active,
        }
