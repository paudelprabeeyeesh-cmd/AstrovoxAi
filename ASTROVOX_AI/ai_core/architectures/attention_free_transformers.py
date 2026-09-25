import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class AttentionFreeTransformer:
    def __init__(self, hidden_size: int = 256):
        self.hidden_size = hidden_size

    def forward(self, hidden_states: list[list[float]]) -> list[list[float]]:
        return hidden_states
