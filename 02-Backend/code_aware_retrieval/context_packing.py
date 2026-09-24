from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass
class ContextItem:
    id: str
    content: str
    recency: float
    graph_distance: int
    is_anchor: bool
    score: float = 0.0


class ContextPacking:
    def __init__(self, budget: int = 2048) -> None:
        self._budget = budget
        self._items: Dict[str, ContextItem] = {}

    def add(self, item: ContextItem) -> None:
        self._items[item.id] = item

    def pack(self) -> List[ContextItem]:
        items = list(self._items.values())
        if not items:
            return []
        np.array([i.id for i in items])
        rec = np.array([i.recency for i in items], dtype=np.float64)
        dist = np.array([i.graph_distance for i in items], dtype=np.int32)
        anchor = np.array([1.0 if i.is_anchor else 0.0 for i in items], dtype=np.float64)
        rec_min, rec_max = rec.min(), rec.max()
        rec_norm = (rec - rec_min) / (rec_max - rec_min + 1e-9)
        dist_max = dist.max() if dist.max() > 0 else 1
        dist_norm = 1.0 - (dist / dist_max)
        scores = 0.5 * rec_norm + 0.3 * dist_norm + 0.2 * anchor + anchor
        for item, s in zip(items, scores):
            item.score = float(s)
        items.sort(key=lambda x: x.score, reverse=True)
        total = 0
        selected: List[ContextItem] = []
        downgrade_queue: List[ContextItem] = []
        for item in items:
            size = len(item.content)
            if total + size <= self._budget:
                selected.append(item)
                total += size
            else:
                downgrade_queue.append(item)
        if downgrade_queue and selected:
            for item in downgrade_queue:
                remaining = self._budget - total
                if remaining <= 0:
                    break
                truncated = item.content[:remaining]
                if truncated:
                    new_item = ContextItem(
                        id=item.id,
                        content=truncated,
                        recency=item.recency,
                        graph_distance=item.graph_distance,
                        is_anchor=item.is_anchor,
                        score=item.score * 0.5,
                    )
                    selected.append(new_item)
                    total += len(truncated)
        return selected

    def set_budget(self, budget: int) -> None:
        self._budget = budget
