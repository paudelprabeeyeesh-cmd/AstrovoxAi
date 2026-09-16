import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Complexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    CREATIVE = "creative"
    AGENTIC = "agentic"


@dataclass
class ModelTier:
    name: str
    provider: str
    model_id: str
    latency_ms: tuple[float, float]
    cost_per_1k_tokens: float
    max_tokens: int = 4096
    enabled: bool = True
    error_count: int = 0
    last_error: float = 0.0
    latencies: list[float] = field(default_factory=list)
    max_latency_samples: int = 100

    def record_latency(self, ms: float):
        self.latencies.append(ms)
        if len(self.latencies) > self.max_latency_samples:
            self.latencies = self.latencies[-self.max_latency_samples :]

    @property
    def latency_p95(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def record_error(self):
        self.error_count += 1
        self.last_error = time.time()
        if self.error_count >= 3:
            self.enabled = False
            logger.warning(f"Auto-disabled {self.model_id} after {self.error_count} errors")

    def record_success(self):
        if self.error_count > 0:
            self.error_count = max(0, self.error_count - 1)


TIER_MODELS = [
    ModelTier("llama-3.3-70b-versatile", "groq", "llama-3.3-70b-versatile", (0.0, 100.0), 0.0, 8192),
    ModelTier("mixtral-8x7b-32768", "groq", "mixtral-8x7b-32768", (0.0, 100.0), 0.0, 32768),
    ModelTier("gemini-2.5-flash", "gemini", "gemini-2.5-flash", (500.0, 2000.0), 0.0001, 8192),
    ModelTier("mistral-medium", "mistral", "mistral-medium", (1000.0, 3000.0), 0.0002, 8192),
    ModelTier("mistral-large-latest", "mistral", "mistral-large-latest", (2000.0, 5000.0), 0.0003, 8192),
    ModelTier("deepseek-chat", "openrouter", "deepseek/deepseek-chat", (2000.0, 5000.0), 0.0, 8192),
    ModelTier("claude-3.5-sonnet", "openrouter", "anthropic/claude-3.5-sonnet", (2000.0, 5000.0), 0.003, 4096),
    ModelTier("gpt-4o", "openrouter", "openai/gpt-4o", (2000.0, 5000.0), 0.005, 4096),
    ModelTier("o1-preview", "openrouter", "openai/o1-preview", (5000.0, 30000.0), 0.015, 4096),
]


class IntelligentRouter:
    def __init__(self):
        self.tiers: dict[str, ModelTier] = {m.name: m for m in TIER_MODELS}
        self.daily_spend: float = 0.0
        self.daily_budget: float = float(os.getenv("DAILY_BUDGET_USD", "10.0"))
        self._lock = threading.Lock()
        self._last_reset = time.time()

    def _reset_daily_if_needed(self):
        now = time.time()
        if now - self._last_reset > 86400:
            with self._lock:
                if now - self._last_reset > 86400:
                    self.daily_spend = 0.0
                    self._last_reset = now

    def estimate_complexity(self, prompt: str, context: dict[str, Any] | None = None) -> Complexity:
        length = len(prompt)
        has_code = any(kw in prompt.lower() for kw in ["def ", "class ", "function", "import ", "```"])
        has_math = any(kw in prompt.lower() for kw in ["solve", "equation", "proof", "calculate", "derivative"])
        has_multi_step = prompt.count("?") > 3 or prompt.count("\n") > 5

        if has_code and has_math and has_multi_step:
            return Complexity.AGENTIC
        if has_code and has_multi_step:
            return Complexity.CREATIVE
        if has_math or has_code:
            return Complexity.COMPLEX
        if length > 500 or has_multi_step:
            return Complexity.MEDIUM
        return Complexity.SIMPLE

    def select_tier(self, complexity: Complexity, latency_target: float | None = None) -> ModelTier:
        tier_map = {
            Complexity.SIMPLE: 1,
            Complexity.MEDIUM: 2,
            Complexity.COMPLEX: 3,
            Complexity.CREATIVE: 4,
            Complexity.AGENTIC: 5,
        }
        preferred_tier = tier_map.get(complexity, 3)
        candidates = [m for m in self.tiers.values() if m.enabled]
        candidates.sort(key=lambda m: m.latency_p95)

        for tier_num in range(preferred_tier, 7):
            for model in candidates:
                low, high = model.latency_ms
                if latency_target is not None:
                    if low <= latency_target <= high:
                        if self._under_budget(model):
                            return model
                else:
                    max_allowed = tier_num * 2000
                    if model.latency_ms[1] <= max_allowed:
                        if self._under_budget(model):
                            return model

        for model in candidates:
            if model.cost_per_1k_tokens == 0.0 and self._under_budget(model):
                return model

        for model in candidates:
            if self._under_budget(model):
                return model

        raise RuntimeError("No available model under current budget")

    def _under_budget(self, model: ModelTier) -> bool:
        self._reset_daily_if_needed()
        projected = self.daily_spend + (model.cost_per_1k_tokens * 0.01)
        return projected <= self.daily_budget

    def record(self, model_name: str, tokens: int = 0, latency_ms: float = 0.0, cached: bool = False):
        model = self.tiers.get(model_name)
        if not model:
            return
        with self._lock:
            model.record_latency(latency_ms)
            model.record_success()
            if not cached:
                cost = model.cost_per_1k_tokens * tokens / 1000.0
                self.daily_spend += cost

    def get_status(self) -> dict[str, Any]:
        self._reset_daily_if_needed()
        return {
            "daily_spend": round(self.daily_spend, 6),
            "daily_budget": self.daily_budget,
            "models": {
                name: {
                    "enabled": m.enabled,
                    "error_count": m.error_count,
                    "latency_p95": m.latency_p95,
                    "cost_per_1k": m.cost_per_1k_tokens,
                }
                for name, m in self.tiers.items()
            },
        }


_router_instance: IntelligentRouter | None = None
_router_lock = threading.Lock()


def get_router() -> IntelligentRouter:
    global _router_instance
    if _router_instance is None:
        with _router_lock:
            if _router_instance is None:
                _router_instance = IntelligentRouter()
    return _router_instance
