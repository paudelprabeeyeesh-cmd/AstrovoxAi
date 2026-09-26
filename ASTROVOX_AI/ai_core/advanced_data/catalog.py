"""AI data catalog."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIDataset:
    dataset_id: str
    name: str
    format: str
    size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIDataCatalog:
    def __init__(self) -> None:
        self._datasets: Dict[str, AIDataset] = {}

    def register(self, dataset: AIDataset) -> None:
        dataset.dataset_id = dataset.dataset_id or uuid.uuid4().hex
        self._datasets[dataset.dataset_id] = dataset

    def search(self, query: str) -> List[AIDataset]:
        return [d for d in self._datasets.values() if query.lower() in d.name.lower()]


ai_data_catalog = AIDataCatalog()
