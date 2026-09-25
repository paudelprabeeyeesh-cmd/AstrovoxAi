import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SSMConfig:
    d_state: int = 16
    d_conv: int = 4
    expand: int = 2
    dt_min: float = 0.001
    dt_max: float = 0.1


class StateSpaceModel:
    def __init__(self, config: SSMConfig):
        self.config = config

    def forward(self, x: list[list[float]]) -> list[list[float]]:
        return x
