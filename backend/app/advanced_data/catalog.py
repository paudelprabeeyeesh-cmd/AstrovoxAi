"""Data catalog for dataset discovery and metadata management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Dataset:
    dataset_id: str
    name: str
    location: str
    format: str
    schema: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    owner: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataCatalog:
    def __init__(self) -> None:
        self._datasets: Dict[str, Dataset] = {}

    def register(self, dataset: Dataset) -> None:
        self._datasets[dataset.dataset_id] = dataset

    def search(self, query: str) -> List[Dataset]:
        query = query.lower()
        return [
            d for d in self._datasets.values()
            if query in d.name.lower() or query in d.format.lower() or any(query in t.lower() for t in d.tags)
        ]

    def get(self, dataset_id: str) -> Optional[Dataset]:
        return self._datasets.get(dataset_id)


data_catalog = DataCatalog()
