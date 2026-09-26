import logging
from typing import Any

logger = logging.getLogger(__name__)


class ThoughtToTextGeneration:
    def __init__(self):
        self.history: list[dict[str, Any]] = []

    def generate(self, neural_embedding: list[float], top_k: int = 1) -> list[str]:
        return ["placeholder_thought"] * top_k
