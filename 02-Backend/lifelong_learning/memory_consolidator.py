from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import random


@dataclass
class Memory:
    memory_id: str
    content: Any
    strength: float = 1.0
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0


class MemoryConsolidator:
    def __init__(self, max_memories: int = 1000, decay_rate: float = 0.01) -> None:
        self.max_memories = max_memories
        self.decay_rate = decay_rate
        self._memories: Dict[str, Memory] = {}
        self._consolidation_log: List[Dict[str, Any]] = []

    def add(self, memory_id: str, content: Any) -> Memory:
        if memory_id in self._memories:
            existing = self._memories[memory_id]
            existing.content = content
            existing.accessed_at = time.time()
            existing.access_count += 1
            return existing
        if len(self._memories) >= self.max_memories:
            self._forget_weakest()
        memory = Memory(memory_id=memory_id, content=content)
        self._memories[memory_id] = memory
        return memory

    def consolidate(self) -> Dict[str, Any]:
        now = time.time()
        consolidated = []
        forgotten = []
        for memory in self._memories.values():
            age = now - memory.created_at
            decay = max(0.0, memory.strength - self.decay_rate * age)
            if decay <= 0.1:
                forgotten.append(memory.memory_id)
            else:
                memory.strength = decay
                memory.accessed_at = now
                consolidated.append(memory.memory_id)
        log_entry = {
            "timestamp": now,
            "consolidated_count": len(consolidated),
            "forgotten_count": len(forgotten),
            "forgotten_ids": forgotten,
        }
        self._consolidation_log.append(log_entry)
        for mid in forgotten:
            del self._memories[mid]
        return log_entry

    def replay(self, k: int = 5) -> List[Memory]:
        memories = sorted(
            self._memories.values(),
            key=lambda m: m.strength,
            reverse=True,
        )
        return memories[:k]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._memories)
        avg_strength = (
            sum(m.strength for m in self._memories.values()) / total if total else 0.0
        )
        return {
            "total_memories": total,
            "average_strength": round(avg_strength, 4),
            "consolidation_runs": len(self._consolidation_log),
        }

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        return self._memories.get(memory_id)

    def _forget_weakest(self) -> None:
        if not self._memories:
            return
        weakest = min(self._memories.values(), key=lambda m: m.strength)
        del self._memories[weakest.memory_id]
