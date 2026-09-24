"""
Cost and Token Tracking - product_polish

Deterministic token counting and cost estimation.
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TokenUsage:
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int = 0
    cost: float = 0.0

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


class CostTokenTracker:
    _DEFAULT_PRICES: Dict[str, Dict[str, float]] = {
        "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
        "gpt-3.5-turbo": {"input_per_1k": 0.0015, "output_per_1k": 0.002},
        "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
    }

    def __init__(self, model_prices: Optional[Dict[str, Dict[str, float]]] = None):
        self._model_prices = model_prices if model_prices is not None else dict(self._DEFAULT_PRICES)
        self._lock = threading.RLock()
        self._records: List[TokenUsage] = []

    @staticmethod
    def count_prompt_tokens(model: str, text: str) -> int:
        return max(1, len(text) // 4)

    @staticmethod
    def count_completion_tokens(model: str, text: str) -> int:
        return max(1, len(text) // 4)

    def _compute_cost(self, model: str, input_tokens: int, output_tokens: int, prices: Dict[str, Dict[str, float]]) -> float:
        if model not in prices:
            return 0.0
        input_cost = (input_tokens / 1000.0) * prices[model]["input_per_1k"]
        output_cost = (output_tokens / 1000.0) * prices[model]["output_per_1k"]
        return input_cost + output_cost

    def record_usage(self, session_id: str, model: str, input_tokens: int, output_tokens: int) -> TokenUsage:
        with self._lock:
            cost = self._compute_cost(model, input_tokens, output_tokens, self._model_prices)
            usage = TokenUsage(
                session_id=session_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
            )
            self._records.append(usage)
            return usage

    def get_session_usage(self, session_id: str) -> List[TokenUsage]:
        with self._lock:
            return [r for r in self._records if r.session_id == session_id]

    def get_model_stats(self, model: str) -> Dict[str, Any]:
        with self._lock:
            records = [r for r in self._records if r.model == model]
            return {
                "calls": len(records),
                "cost": sum(r.cost for r in records),
                "input_tokens": sum(r.input_tokens for r in records),
                "output_tokens": sum(r.output_tokens for r in records),
            }

    def get_session_cost(self, session_id: str) -> float:
        with self._lock:
            return sum(r.cost for r in self._records if r.session_id == session_id)

    def get_total_cost(self) -> float:
        with self._lock:
            return sum(r.cost for r in self._records)

    def get_total_tokens(self) -> Dict[str, int]:
        with self._lock:
            input_tokens = sum(r.input_tokens for r in self._records)
            output_tokens = sum(r.output_tokens for r in self._records)
            return {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            }

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            model_stats = {}
            for r in self._records:
                if r.model not in model_stats:
                    model_stats[r.model] = {"calls": 0, "cost": 0.0, "tokens": 0}
                model_stats[r.model]["calls"] += 1
                model_stats[r.model]["cost"] += r.cost
                model_stats[r.model]["tokens"] += r.total_tokens
            return {
                "total_cost": self.get_total_cost(),
                "total_calls": len(self._records),
                "tokens": self.get_total_tokens(),
                "model_stats": model_stats,
            }

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._records = [r for r in self._records if r.session_id != session_id]

    def reset(self) -> None:
        with self._lock:
            self._records.clear()
