"""
Model router with fallback, load balancing, and tier routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelEndpoint:
    name: str
    provider: str
    model_id: str
    latency_ms: float = 100.0
    error_rate: float = 0.0
    cost_per_1k_tokens: float = 0.0
    max_context: int = 4096
    capabilities: List[str] = None
    priority: int = 1

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["chat", "completion"]


class ModelRouter:
    """Routes requests to models with fallback and load balancing."""

    def __init__(self):
        self.endpoints: Dict[str, ModelEndpoint] = {}
        self.fallback_chain: List[str] = []
        self.request_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}

    def register_endpoint(self, endpoint: ModelEndpoint):
        self.endpoints[endpoint.name] = endpoint
        self.request_counts[endpoint.name] = 0
        self.error_counts[endpoint.name] = 0

    def set_fallback_chain(self, chain: List[str]):
        self.fallback_chain = chain

    def select_model(self, capabilities: List[str], max_context: int, budget: Optional[float] = None) -> Optional[ModelEndpoint]:
        candidates = []
        for endpoint in self.endpoints.values():
            if not all(cap in endpoint.capabilities for cap in capabilities):
                continue
            if max_context > endpoint.max_context:
                continue
            if budget is not None and endpoint.cost_per_1k_tokens > budget:
                continue
            score = (1.0 / (endpoint.latency_ms + 1)) * (1.0 - endpoint.error_rate) * endpoint.priority
            candidates.append((score, endpoint))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def get_fallback(self, failed_model: str) -> Optional[ModelEndpoint]:
        idx = self.fallback_chain.index(failed_model) if failed_model in self.fallback_chain else -1
        for next_model in self.fallback_chain[idx + 1 :]:
            if next_model in self.endpoints:
                return self.endpoints[next_model]
        return None

    def record_request(self, model_name: str, success: bool, latency_ms: float):
        self.request_counts[model_name] = self.request_counts.get(model_name, 0) + 1
        if not success:
            self.error_counts[model_name] = self.error_counts.get(model_name, 0) + 1
        endpoint = self.endpoints.get(model_name)
        if endpoint:
            alpha = 0.1
            endpoint.latency_ms = (1 - alpha) * endpoint.latency_ms + alpha * latency_ms
            total = self.request_counts[model_name]
            errors = self.error_counts.get(model_name, 0)
            endpoint.error_rate = errors / max(total, 1)

    def get_stats(self) -> dict:
        return {
            "endpoints": len(self.endpoints),
            "total_requests": sum(self.request_counts.values()),
            "errors": sum(self.error_counts.values()),
            "endpoint_stats": {
                name: {"requests": self.request_counts.get(name, 0), "errors": self.error_counts.get(name, 0), "latency_ms": ep.latency_ms, "error_rate": ep.error_rate}
                for name, ep in self.endpoints.items()
            },
        }
