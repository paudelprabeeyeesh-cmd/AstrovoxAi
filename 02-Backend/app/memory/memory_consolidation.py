"""Memory consolidation and promotion between tiers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ConsolidatedMemory:
    memory_id: str
    content: str
    source_memories: List[str]
    consolidated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryConsolidator:
    """Consolidate and promote memories across tiers."""

    def __init__(self):
        self._consolidated: Dict[str, ConsolidatedMemory] = {}

    def consolidate(self, memory_ids: List[str], contents: Dict[str, str]) -> ConsolidatedMemory:
        memory_id = f"consolidated_{datetime.now(timezone.utc).timestamp()}"
        merged = "\n".join(contents[mid] for mid in memory_ids if mid in contents)
        consolidated = ConsolidatedMemory(
            memory_id=memory_id,
            content=merged,
            source_memories=memory_ids,
        )
        self._consolidated[memory_id] = consolidated
        return consolidated

    def promote(self, memory_id: str, target_tier: str) -> bool:
        return memory_id in self._consolidated
