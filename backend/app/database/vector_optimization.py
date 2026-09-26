"""Vector database optimization with quantization and tiered storage."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VectorIndexConfig:
    dimension: int
    max_elements: int = 10000
    M: int = 16
    ef_construction: int = 200
    ef_search: int = 50
    quantization: str = "none"
    tiered_storage: bool = False


@dataclass
class TieredNode:
    id: str
    vector: List[float]
    tier: str = "hot"
    quantized: Optional[List[float]] = None


class VectorIndexOptimizer:
    def __init__(self, config: VectorIndexConfig):
        self.config = config
        self._nodes: Dict[str, TieredNode] = {}
        self._quantization_bins: int = 256

    def quantize(self, vector: List[float]) -> List[float]:
        if self.config.quantization == "none":
            return vector
        if self.config.quantization == "scalar":
            return [round(v * self._quantization_bins) / self._quantization_bins for v in vector]
        if self.config.quantization == "binary":
            return [1.0 if v > 0 else 0.0 for v in vector]
        return vector

    def add(self, id: str, vector: List[float]) -> None:
        quantized = self.quantize(vector)
        tier = "hot" if len(self._nodes) < self.config.max_elements // 2 else "warm"
        self._nodes[id] = TieredNode(id=id, vector=vector, tier=tier, quantized=quantized)

    def search(self, query: List[float], k: int = 10, tier_filter: Optional[str] = None) -> List[Tuple[str, float]]:
        candidates = [
            (nid, node.vector) for nid, node in self._nodes.items()
            if tier_filter is None or node.tier == tier_filter
        ]
        if not candidates:
            return []
        scored = [(nid, self._distance(query, vec)) for nid, vec in candidates]
        scored.sort(key=lambda x: x[1])
        return scored[:k]

    def evict_to_cold(self, target_count: int) -> List[str]:
        evicted = []
        warm_nodes = [nid for nid, node in self._nodes.items() if node.tier == "warm"]
        for nid in warm_nodes[: max(0, len(self._nodes) - target_count)]:
            self._nodes[nid].tier = "cold"
            evicted.append(nid)
        return evicted

    def _distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def get_stats(self) -> Dict[str, Any]:
        tiers = {"hot": 0, "warm": 0, "cold": 0}
        for node in self._nodes.values():
            tiers[node.tier] = tiers.get(node.tier, 0) + 1
        return {
            "total": len(self._nodes),
            "tiers": tiers,
            "quantization": self.config.quantization,
        }
