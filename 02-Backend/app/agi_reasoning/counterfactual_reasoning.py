import logging
from typing import Any

logger = logging.getLogger(__name__)


class CounterfactualReasoningService:
    def generate(self, premise: str, intervention: str, outcome: str) -> dict[str, Any]:
        return {"premise": premise, "intervention": intervention, "outcome": outcome, "probability": 0.5}

    def closest_worlds(self, cf_id: str, k: int = 5) -> list[dict[str, Any]]:
        return [{"world": i, "similarity": 1.0 / (i + 1)} for i in range(k)]
