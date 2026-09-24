from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class AttentionItem:
    content: Any
    priority: float
    timestamp: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class AttentionMechanism:
    def __init__(self, capacity: int = 7, decay_rate: float = 0.01):
        self.capacity = capacity
        self.decay_rate = decay_rate
        self.items: List[AttentionItem] = []
        self.attention_log: List[Dict[str, Any]] = []

    def attend(self, items: List[Any], priorities: Optional[List[float]] = None) -> List[int]:
        if priorities is None:
            priorities = [1.0] * len(items)
        scored = [(i, p) for i, p in enumerate(priorities)]
        scored.sort(key=lambda x: x[1], reverse=True)
        attended = [i for i, _ in scored[: self.capacity]]
        self.attention_log.append({
            "timestamp": time.time(),
            "attended_indices": attended,
            "count": len(attended),
        })
        for idx in attended:
            if idx < len(self.items):
                self.items[idx].access_count += 1
                self.items[idx].last_accessed = time.time()
        return attended

    def add_item(self, content: Any, priority: float, timestamp: float) -> bool:
        if len(self.items) >= self.capacity:
            self._evict_lowest()
        item = AttentionItem(content=content, priority=priority, timestamp=timestamp)
        self.items.append(item)
        return True

    def _evict_lowest(self) -> None:
        if not self.items:
            return
        min_idx = min(range(len(self.items)), key=lambda i: self.items[i].priority)
        self.items.pop(min_idx)

    def get_attended_content(self, indices: List[int]) -> List[Any]:
        return [self.items[i].content for i in indices if 0 <= i < len(self.items)]

    def get_state(self) -> Dict[str, Any]:
        return {
            "items": [{"content": item.content, "priority": item.priority} for item in self.items],
            "capacity": self.capacity,
            "utilization": len(self.items) / self.capacity if self.capacity > 0 else 0.0,
        }

    def step(self, dt: float = 1.0) -> None:
        for item in self.items:
            item.last_accessed += dt
