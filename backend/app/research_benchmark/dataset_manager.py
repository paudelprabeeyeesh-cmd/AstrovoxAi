"""Dataset manager for research benchmarks."""
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
    description: str
    format: str
    size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetManager:
    def __init__(self) -> None:
        self._datasets: Dict[str, Dataset] = {}

    def register(self, dataset: Dataset) -> Dataset:
        dataset.dataset_id = dataset.dataset_id or uuid.uuid4().hex
        self._datasets[dataset.dataset_id] = dataset
        return dataset

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        return self._datasets.get(dataset_id)

    def list_datasets(self) -> List[Dataset]:
        return list(self._datasets.values())


dataset_manager = DatasetManager()
