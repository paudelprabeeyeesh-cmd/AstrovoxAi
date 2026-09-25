import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LinearAttentionConfig:
    hidden_size: int = 256
    num_heads: int = 8
    kernel_features: int = 128


class LinearAttention:
    def __init__(self, config: LinearAttentionConfig):
        self.config = config

    def forward(self, query: list[list[float]], key: list[list[float]], value: list[list[float]]) -> list[list[float]]:
        return [[0.0] * self.config.hidden_size for _ in range(len(query))]
