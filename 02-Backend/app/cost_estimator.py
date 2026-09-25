"""Per-request cost estimation for AI inference."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from .shared import MODEL_COSTS
from .cost import count_tokens

logger = logging.getLogger(__name__)


@dataclass
class RequestCostEstimate:
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    currency: str = "USD"
    pricing_source: str = "static"
    timestamp: float = field(default_factory=time.time)


class CostEstimator:
    def __init__(self):
        self._history: list[RequestCostEstimate] = []

    def estimate(
        self,
        model: str,
        prompt: str,
        system_prompt: str = "",
        expected_output_tokens: Optional[int] = None,
        provider: str = "unknown",
    ) -> RequestCostEstimate:
        input_tokens = count_tokens(prompt) + count_tokens(system_prompt)
        output_tokens = expected_output_tokens or max(1, len(prompt.split()) // 2)
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = costs["input"] * input_tokens / 1000
        output_cost = costs["output"] * output_tokens / 1000
        estimated_cost = round(input_cost + output_cost, 6)
        estimate = RequestCostEstimate(
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
        )
        self._history.append(estimate)
        return estimate

    def record_actual(self, estimate: RequestCostEstimate, actual_input_tokens: int, actual_output_tokens: int) -> RequestCostEstimate:
        costs = MODEL_COSTS.get(estimate.model, {"input": 0, "output": 0})
        input_cost = costs["input"] * actual_input_tokens / 1000
        output_cost = costs["output"] * actual_output_tokens / 1000
        actual_cost = round(input_cost + output_cost, 6)
        estimate.input_tokens = actual_input_tokens
        estimate.output_tokens = actual_output_tokens
        estimate.estimated_cost = actual_cost
        return estimate

cost_estimator = CostEstimator()
        if since is None:
            return sum(e.estimated_cost for e in self._history)
        return sum(e.estimated_cost for e in self._history if e.timestamp >= since)
