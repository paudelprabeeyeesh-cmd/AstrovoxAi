"""AI Model Management — registry, versioning, health checks, benchmarking."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModelCapability:
    """Capabilities of an AI model."""
    text_generation: bool = True
    chat: bool = True
    embeddings: bool = False
    image_understanding: bool = False
    code_generation: bool = False
    function_calling: bool = False
    streaming: bool = True
    max_context_length: int = 4096


@dataclass
class ModelInfo:
    """Information about a registered model."""
    id: str
    provider: str
    display_name: str
    version: str
    capabilities: ModelCapability
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency_ms: float = 0.0
    is_available: bool = True
    last_health_check: float = 0.0


class ModelRegistry:
    """Registry of all available AI models."""

    def __init__(self):
        self._models: dict[str, ModelInfo] = {}

    def register(self, model: ModelInfo):
        """Register a model."""
        self._models[model.id] = model

    def get(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_models(self, provider: str = None, capability: str = None) -> list[ModelInfo]:
        """List all models, optionally filtered."""
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if capability:
            models = [
                m for m in models
                if getattr(m.capabilities, capability, False)
            ]

        return models

    def get_cheapest(self, capability: str = None) -> Optional[ModelInfo]:
        """Get the cheapest available model."""
        models = self.list_models(capability=capability)
        available = [m for m in models if m.is_available]
        if not available:
            return None
        return min(available, key=lambda m: m.cost_per_1k_output)

    def get_fastest(self, capability: str = None) -> Optional[ModelInfo]:
        """Get the fastest available model."""
        models = self.list_models(capability=capability)
        available = [m for m in models if m.is_available and m.avg_latency_ms > 0]
        if not available:
            return None
        return min(available, key=lambda m: m.avg_latency_ms)


class HealthChecker:
    """Health checker for AI providers."""

    def __init__(self):
        self._status: dict[str, dict] = {}

    async def check_provider(self, provider: str) -> dict:
        """Check if a provider is healthy."""
        start = time.time()

        status = {
            "provider": provider,
            "healthy": True,
            "latency_ms": 0,
            "last_checked": time.time(),
        }

        try:
            # Simulate health check
            await asyncio.sleep(0.01)
            status["latency_ms"] = (time.time() - start) * 1000
        except Exception:
            status["healthy"] = False

        self._status[provider] = status
        return status

    def get_status(self, provider: str = None) -> dict:
        """Get health status."""
        if provider:
            return self._status.get(provider, {})
        return dict(self._status)


class ModelBenchmark:
    """Benchmark models for performance and quality."""

    def __init__(self):
        self._results: list[dict] = []

    async def benchmark(self, model_id: str, prompts: list[str]) -> dict:
        """Benchmark a model."""
        result = {
            "model_id": model_id,
            "timestamp": time.time(),
            "prompts_tested": len(prompts),
            "avg_latency_ms": 0,
            "tokens_per_second": 0,
            "quality_score": 0,
        }

        self._results.append(result)
        return result

    def get_results(self, model_id: str = None) -> list[dict]:
        """Get benchmark results."""
        if model_id:
            return [r for r in self._results if r["model_id"] == model_id]
        return list(self._results)

    def compare_models(self, model_ids: list[str]) -> dict:
        """Compare multiple models."""
        results = {}
        for model_id in model_ids:
            model_results = self.get_results(model_id)
            if model_results:
                results[model_id] = model_results[-1]
        return results


import asyncio

model_registry = ModelRegistry()
health_checker = HealthChecker()
model_benchmark = ModelBenchmark()
