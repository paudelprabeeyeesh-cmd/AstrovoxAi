"""Batched inference for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BatchRequest:
    """A batched inference request."""
    items: list[dict] = field(default_factory=list)
    batch_size: int = 32

    def add(self, item: dict) -> None:
        self.items.append(item)


@dataclass
class BatchResult:
    """A batched inference result."""
    predictions: list[Any] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"predictions": self.predictions, "metadata": self.metadata}


class BatchInference:
    """Batched inference processing."""

    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self.processed = 0
        self.batches = 0

    def submit(self, items: list[dict]) -> BatchResult:
        results = []
        for item in items:
            # Placeholder inference logic
            results.append({"id": item.get("id"), "label": "prediction", "confidence": 0.9})
        self.processed += len(items)
        self.batches += 1
        return BatchResult(predictions=results)

    def submit_batched(self, items: list[dict]) -> list[BatchResult]:
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            results.append(self.submit(batch))
        self.processed += len(items)
        self.batches += len(results)
        return results

    def stats(self) -> dict:
        return {"processed": self.processed, "batches": self.batches,
                "batch_size": self.batch_size}
