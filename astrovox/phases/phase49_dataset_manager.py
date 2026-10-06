"""Dataset manager for Astrovox training."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DatasetRecord:
    """A dataset registry entry."""
    id: str
    name: str
    path: str
    size: int = 0
    rows: int = 0
    created: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "path": self.path, "size": self.size,
                "rows": self.rows}


class DatasetManager:
    """Dataset registry and loading."""

    def __init__(self):
        self.datasets: dict[str, DatasetRecord] = {}

    def register(self, name: str, path: str, size: int = 0, rows: int = 0) -> DatasetRecord:
        ds_id = f"ds_{len(self.datasets)}"
        rec = DatasetRecord(id=ds_id, name=name, path=path, size=size, rows=rows)
        self.datasets[ds_id] = rec
        return rec

    def get(self, ds_id: str) -> DatasetRecord | None:
        return self.datasets.get(ds_id)

    def load(self, ds_id: str, split: str = "train") -> Any:
        ds = self.get(ds_id)
        if ds is None:
            raise KeyError(f"Dataset {ds_id} not found")
        return {"id": ds_id, "split": split}  # placeholder load

    def list_datasets(self) -> list[DatasetRecord]:
        return list(self.datasets.values())

    def delete(self, ds_id: str) -> bool:
        if ds_id in self.datasets:
            del self.datasets[ds_id]
            return True
        return False

    def count(self) -> int:
        return len(self.datasets)
