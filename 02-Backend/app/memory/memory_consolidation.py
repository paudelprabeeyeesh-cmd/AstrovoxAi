"""
Memory Consolidation Service.

Bridges DB-stored memories with the in-memory consolidator.
Runs consolidation strategies:
- Duplicate detection and merging
- Episodic-to-semantic consolidation
- Importance strengthening
- Stale memory pruning
- Conversation summary generation
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from memory_persistence.memory_consolidation import (
    MemoryConsolidator,
    MemoryFragment,
)

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationRecord:
    memory_id: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryConsolidationService:
    """
    Service for consolidating DB-stored memories.

    Loads memories from the database, runs consolidation strategies,
    and writes back results including summaries and pruned entries.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        stale_days: int = 90,
    ):
        self.similarity_threshold = similarity_threshold
        self.stale_days = stale_days
        self._consolidator = MemoryConsolidator(
            similarity_threshold=similarity_threshold,
            stale_days=stale_days,
        )
        self._lock = threading.RLock()
        self._records: List[ConsolidationRecord] = []

    def _get_connection(self):
        from app.database import get_db
        return get_db()

    def load_user_memories(self, user_id: str, limit: int = 500) -> List[MemoryFragment]:
        """Load user memories from DB into the consolidator."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, key, value, embedding, memory_type, importance_score, is_deleted, created_at
                FROM memories
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        fragments: List[MemoryFragment] = []
        for row in rows:
            embedding = None
            if row.get("embedding"):
                try:
                    import json
                    embedding = np.array(json.loads(row["embedding"]), dtype=np.float32)
                except Exception:
                    embedding = None

            is_deleted = bool(row.get("is_deleted")) if row.get("is_deleted") is not None else False
            fragments.append(
                MemoryFragment(
                    memory_id=row["id"],
                    content=row.get("value") or row.get("key") or "",
                    embedding=embedding,
                    importance=float(row.get("importance_score") or 0.5),
                    created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.utcnow(),
                    category=row.get("memory_type") or "general",
                    metadata={"key": row.get("key"), "memory_type": row.get("memory_type")},
                    is_deleted=is_deleted,
                )
            )
        return fragments

    def consolidate_user(self, user_id: str) -> Dict[str, Any]:
        """Run consolidation for all memories of a user."""
        with self._lock:
            fragments = self.load_user_memories(user_id)
            self._consolidator.add_memories(fragments)
            result = self._consolidator.consolidate_all()
            self._records.append(
                ConsolidationRecord(
                    memory_id=user_id,
                    action="user_consolidation",
                    details=result,
                )
            )
            try:
                self._writeback_user_memories(user_id)
            except Exception as _e:  # noqa: BLE001
                logger.warning("Memory consolidation writeback failed: %s", _e)
            return {
                "user_id": user_id,
                "loaded": len(fragments),
                **result,
            }

    def _writeback_user_memories(self, user_id: str) -> None:
        with self._get_connection() as conn:
            for fragment in self._consolidator._memories.values():
                if fragment.is_deleted:
                    conn.execute(
                        "UPDATE memories SET is_deleted = 1 WHERE id = ?",
                        (fragment.memory_id,),
                    )
                else:
                    conn.execute(
                        "UPDATE memories SET importance_score = ? WHERE id = ?",
                        (float(fragment.importance), fragment.memory_id),
                    )
            conn.commit()

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get consolidation stats for a user."""
        fragments = self.load_user_memories(user_id)
        if not fragments:
            return {"total_memories": 0, "active_memories": 0}
        active = [f for f in fragments if not f.is_deleted]
        return {
            "total_memories": len(fragments),
            "active_memories": len(active),
            "avg_importance": float(np.mean([f.importance for f in active])) if active else 0.0,
            "by_category": self._count_by_category(fragments),
        }

    def _count_by_category(self, fragments: List[MemoryFragment]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in fragments:
            if f.is_deleted:
                continue
            cat = f.category or "general"
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def get_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._records[-limit:]]


consolidation_service = MemoryConsolidationService()
