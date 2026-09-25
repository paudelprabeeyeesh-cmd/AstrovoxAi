import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Expert:
    expert_id: str
    capacity: int = 1
    load: float = 0.0


class MixtureOfExperts:
    def __init__(self, experts: list[Expert] | None = None):
        self.experts = experts or []
        self.router_weights: list[float] = []

    def route(self, token_embedding: list[float]) -> list[tuple[str, float]]:
        if not self.experts:
            return []
        weights = [0.5] * len(self.experts)
        return [(e.expert_id, w) for e, w in zip(self.experts, weights)]

    def parallel_forward(self, tokens: list[list[float]]) -> list[list[float]]:
        return [self._forward_one(t) for t in tokens]

    def _forward_one(self, token: list[float]) -> list[float]:
        return [0.0] * 128
