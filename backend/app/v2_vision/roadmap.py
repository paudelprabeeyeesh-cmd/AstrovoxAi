"""Roadmap for v2.0 vision."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RoadmapItem:
    item_id: str
    title: str
    description: str
    priority: int
    status: str
    target_quarter: str


class Roadmap:
    def __init__(self) -> None:
        self._items: List[RoadmapItem] = []

    def add_item(self, item: RoadmapItem) -> None:
        self._items.append(item)

    def get_items(self, quarter: Optional[str] = None) -> List[RoadmapItem]:
        if quarter:
            return [item for item in self._items if item.target_quarter == quarter]
        return list(self._items)


roadmap = Roadmap()
