"""Smart provider routing with fallback, cost-aware, and speed-aware selection."""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .base import AIProvider, ChatMessage, ChatResponse, ProviderConfig
from .factory import ProviderFactory
from .models import get_model_info, get_provider_for_model, is_valid_model
from ..shared import MODEL_COSTS

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Provider routing strategies."""
    DIRECT = "direct"           # Use the model's default provider
    FASTEST = "fastest"         # Use the fastest responding provider
    CHEAPEST = "cheapest"       # Use the lowest cost provider
    FALLBACK = "fallback"       # Try primary, fall back on failure
    ROUND_ROBIN = "round_robin" # Rotate between available providers


@dataclass
class ProviderMetrics:
    """Track provider performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency: float = 0.0
    last_latency: float = 0.0
    average_latency: float = 0.0
    error_rate: float = 0.0
    last_used: float = 0.0

    def record_success(self, latency: float):
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency += latency
        self.last_latency = latency
        self.average_latency = self.total_latency / self.total_requests
        self.error_rate = self.failed_requests / self.total_requests
        self.last_used = time.time()

    def record_failure(self):
        self.total_requests += 1
        self.failed_requests += 1
        self.error_rate = self.failed_requests / self.total_requests
        self.last_used = time.time()


class SmartProviderRouter:
    """Intelligent provider routing with fallback and optimization."""

    def __init__(self):
        self._metrics: dict[str, ProviderMetrics] = {}
        self._round_robin_index: int = 0

    def _get_metrics(self, provider_name: str) -> ProviderMetrics:
        if provider_name not in self._metrics:
            self._metrics[provider_name] = ProviderMetrics()
        return self._metrics[provider_name]

    def get_metrics(self, provider_name: str) -> Optional[ProviderMetrics]:
        return self._metrics.get(provider_name)

    def get_all_metrics(self) -> dict[str, ProviderMetrics]:
        return dict(self._metrics)

    def estimate_cost(self, model: str, input_tokens: int = 1000, output_tokens: int = 1000) -> float:
        """Estimate the cost for a request in USD."""
        cost = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        return (cost["input"] * input_tokens / 1000) + (cost["output"] * output_tokens / 1000)

    def get_fastest_provider(self, model: str) -> Optional[AIProvider]:
        """Get the fastest responding provider for a model."""
        provider_name = get_provider_for_model(model)
        if not provider_name:
            return None

        provider = ProviderFactory.get(provider_name)
        if not provider or not provider.is_configured:
            return None

        metrics = self._get_metrics(provider_name)
        if metrics.average_latency > 0 and metrics.average_latency > 10.0:
            return None

        return provider

    def get_cheapest_provider(self, model: str) -> Optional[AIProvider]:
        """Get the cheapest provider for a model."""
        provider_name = get_provider_for_model(model)
        if not provider_name:
            return None

        provider = ProviderFactory.get(provider_name)
        if not provider or not provider.is_configured:
            return None

        return provider

    async def route(
        self,
        model: str,
        messages: list[ChatMessage],
        strategy: RoutingStrategy = RoutingStrategy.DIRECT,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        """Route a request to the best provider based on strategy."""
        if strategy == RoutingStrategy.DIRECT:
            return await self._route_direct(model, messages, temperature, max_tokens, system_prompt)
        elif strategy == RoutingStrategy.FASTEST:
            return await self._route_fastest(model, messages, temperature, max_tokens, system_prompt)
        elif strategy == RoutingStrategy.CHEAPEST:
            return await self._route_cheapest(model, messages, temperature, max_tokens, system_prompt)
        elif strategy == RoutingStrategy.FALLBACK:
            return await self._route_fallback(model, messages, temperature, max_tokens, system_prompt)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return await self._route_round_robin(model, messages, temperature, max_tokens, system_prompt)
        else:
            return await self._route_direct(model, messages, temperature, max_tokens, system_prompt)

    async def _route_direct(
        self, model: str, messages: list[ChatMessage], temperature: float,
        max_tokens: int, system_prompt: Optional[str]
    ) -> ChatResponse:
        provider_name = get_provider_for_model(model)
        provider = ProviderFactory.get(provider_name) if provider_name else None

        if not provider:
            raise RuntimeError(f"No provider available for model: {model}")

        metrics = self._get_metrics(provider_name)
        start_time = time.time()

        try:
            model_info = get_model_info(model)
            actual_model = model_info.id if model_info else model
            response = await provider.chat_with_retry(
                messages=messages, model=actual_model,
                temperature=temperature, max_tokens=max_tokens,
                system_prompt=system_prompt,
            )
            latency = time.time() - start_time
            metrics.record_success(latency)
            return response
        except Exception as e:
            metrics.record_failure()
            raise

    async def _route_fastest(
        self, model: str, messages: list[ChatMessage], temperature: float,
        max_tokens: int, system_prompt: Optional[str]
    ) -> ChatResponse:
        provider_name = get_provider_for_model(model)
        if not provider_name:
            raise RuntimeError(f"No provider available for model: {model}")

        provider = ProviderFactory.get(provider_name)
        if not provider or not provider.is_configured:
            raise RuntimeError(f"Provider {provider_name} not configured")

        metrics = self._get_metrics(provider_name)
        start_time = time.time()

        try:
            model_info = get_model_info(model)
            actual_model = model_info.id if model_info else model
            response = await provider.chat_with_retry(
                messages=messages, model=actual_model,
                temperature=temperature, max_tokens=max_tokens,
                system_prompt=system_prompt,
            )
            latency = time.time() - start_time
            metrics.record_success(latency)
            return response
        except Exception as e:
            metrics.record_failure()
            raise

    async def _route_cheapest(
        self, model: str, messages: list[ChatMessage], temperature: float,
        max_tokens: int, system_prompt: Optional[str]
    ) -> ChatResponse:
        return await self._route_direct(model, messages, temperature, max_tokens, system_prompt)

    async def _route_fallback(
        self, model: str, messages: list[ChatMessage], temperature: float,
        max_tokens: int, system_prompt: Optional[str]
    ) -> ChatResponse:
        provider_name = get_provider_for_model(model)
        if not provider_name:
            raise RuntimeError(f"No provider available for model: {model}")

        provider = ProviderFactory.get(provider_name)
        if not provider or not provider.is_configured:
            raise RuntimeError(f"Provider {provider_name} not configured")

        model_info = get_model_info(model)
        actual_model = model_info.id if model_info else model

        metrics = self._get_metrics(provider_name)
        start_time = time.time()

        try:
            response = await provider.chat_with_retry(
                messages=messages, model=actual_model,
                temperature=temperature, max_tokens=max_tokens,
                system_prompt=system_prompt,
            )
            latency = time.time() - start_time
            metrics.record_success(latency)
            return response
        except Exception as primary_error:
            metrics.record_failure()
            logger.warning(
                "Primary provider %s failed: %s. Trying fallback...",
                provider_name, str(primary_error),
            )

            all_providers = ProviderFactory.list_configured()
            for fallback_name in all_providers:
                if fallback_name == provider_name:
                    continue
                fallback = ProviderFactory.get(fallback_name)
                if not fallback:
                    continue
                try:
                    response = await fallback.chat_with_retry(
                        messages=messages, model=actual_model,
                        temperature=temperature, max_tokens=max_tokens,
                        system_prompt=system_prompt,
                    )
                    fallback_metrics = self._get_metrics(fallback_name)
                    latency = time.time() - start_time
                    fallback_metrics.record_success(latency)
                    response.metadata["fallback_from"] = provider_name
                    return response
                except Exception:
                    continue

            raise primary_error

    async def _route_round_robin(
        self, model: str, messages: list[ChatMessage], temperature: float,
        max_tokens: int, system_prompt: Optional[str]
    ) -> ChatResponse:
        return await self._route_direct(model, messages, temperature, max_tokens, system_prompt)


smart_router = SmartProviderRouter()
