from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AutobiographicalMemory:
    id: str
    event_type: str
    content: Any
    emotional_valence: float
    importance: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    related_memories: list[str] = field(default_factory=list)


class AutobiographicalMemorySystem:
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.memories: dict[str, AutobiographicalMemory] = {}
        self.timeline: list[AutobiographicalMemory] = []
        self.episodic_index: dict[str, list[str]] = {}
        self.semantic_index: dict[str, list[str]] = {}

    def store(self, memory: AutobiographicalMemory) -> str:
        if len(self.memories) >= self.capacity:
            self._forget_least_important()
        self.memories[memory.id] = memory
        self.timeline.append(memory)
        self.timeline.sort(key=lambda m: m.timestamp)
        for tag in memory.tags:
            self.semantic_index.setdefault(tag, []).append(memory.id)
        self.episodic_index.setdefault(memory.event_type, []).append(memory.id)
        return memory.id

    def recall(self, query: str, limit: int = 10) -> list[AutobiographicalMemory]:
        results = []
        if query in self.episodic_index:
            for mid in self.episodic_index[query]:
                if mid in self.memories:
                    results.append(self.memories[mid])
        for tag, ids in self.semantic_index.items():
            if query.lower() in tag.lower():
                for mid in ids:
                    if mid in self.memories:
                        results.append(self.memories[mid])
        seen = set()
        unique = []
        for m in results:
            if m.id not in seen:
                seen.add(m.id)
                unique.append(m)
        unique.sort(key=lambda m: m.importance, reverse=True)
        return unique[:limit]

    def _forget_least_important(self):
        if not self.memories:
            return
        least = min(self.memories.values(), key=lambda m: m.importance)
        del self.memories[least.id]

    def get_life_summary(self) -> dict[str, Any]:
        if not self.memories:
            return {"total_memories": 0}
        return {
            "total_memories": len(self.memories),
            "event_types": list(self.episodic_index.keys()),
            "recent_events": [m.content for m in self.timeline[-5:]],
            "avg_importance": sum(m.importance for m in self.memories.values()) / len(self.memories),
        }
