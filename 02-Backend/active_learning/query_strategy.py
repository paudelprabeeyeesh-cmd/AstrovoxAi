import math
import random
from typing import List, Sequence, Dict, Any


class QueryStrategy:
    UNCERTAINTY = "uncertainty"
    ENTROPY = "entropy"
    MARGIN = "margin"
    RANDOM = "random"
    EXPECTED_LEARNING_GAIN = "expected_learning_gain"

    _ALL = [UNCERTAINTY, ENTROPY, MARGIN, RANDOM, EXPECTED_LEARNING_GAIN]

    @classmethod
    def all(cls) -> List[str]:
        return list(cls._ALL)

    @classmethod
    def validate(cls, name: str) -> str:
        if name not in cls._ALL:
            raise ValueError(
                f"Unknown strategy: {name}. Valid options: {cls._ALL}"
            )
        return name
