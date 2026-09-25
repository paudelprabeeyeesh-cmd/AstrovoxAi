"""Memory ranking and retrieval ranking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RankedMemory:
    memory_id: str
    content: str
    score: float
    memory_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryRanker:
    """Rank memories by relevance and importance."""

    def rank(self, memories: List[Dict[str, Any]], query: str, limit: int = 10) -> List[RankedMemory]:
        query_terms = set(query.lower().split())
        scored = []
        for mem in memories:
            content = mem.get("content", "")
            terms = set(content.lower().split())
            overlap = len(query_terms & terms)
            importance = mem.get("importance", 0.5)
            recency = 1.0
            if "last_accessed" in mem:
                try:
                    last = datetime.fromisoformat(mem["last_accessed"])
                    age_days = (datetime.now(timezone.utc) - last).total_seconds() / 86400.0
                    recency = max(0.0, 1.0 - age_days / 365.0)
                except Exception:
                    pass
            score = overlap / max(len(query_terms), 1) + importance * 0.5 + recency * 0.3
            scored.append(RankedMemory(
                memory_id=mem.get("memory_id", ""),
                content=content,
                score=score,
                memory_type=mem.get("memory_type", "unknown"),
                metadata=mem.get("metadata", {}),
            ))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]
