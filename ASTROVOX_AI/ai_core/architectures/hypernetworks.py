import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HypernetworkConfig:
    input_dim: int
    output_dim: int
    hidden_dim: int = 256


class Hypernetwork:
    def __init__(self, config: HypernetworkConfig):
        self.config = config

    def generate_weights(self, context: list[float]) -> list[list[float]]:
        return [[0.1] * self.config.output_dim for _ in range(self.config.input_dim)]
