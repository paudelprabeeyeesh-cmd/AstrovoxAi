"""Tests for the multi-model router."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.model_router_v2 import (
    MultiModelRouter,
    RoutingRequest,
    RoutingPolicy,
    FallbackStrategy,
    RoutingResult,
)
from app.intelligence.execution_tracer import ExecutionTracer


def _make_tracer():
    tracer = ExecutionTracer()
    tracer.start_trace(request_id="trace-1", user_id=1, user_message="hello")
    return tracer


class TestMultiModelRouter:
    def test_route_returns_result(self):
        router = MultiModelRouter()
        tracer = _make_tracer()
        req = RoutingRequest(
            user_id=1,
            task_type="general_chat",
            optimize_for="cost",
            policy=RoutingPolicy.BALANCED,
            fallback_strategy=FallbackStrategy.CROSS_PROVIDER,
            trace=tracer,
            request_id="trace-1",
        )
        result = asyncio.run(router.route(req))
        assert result is not None
        assert isinstance(result, RoutingResult)
        assert result.model_id
        assert result.provider_name

    def test_route_preferred_model(self):
        router = MultiModelRouter()
        tracer = _make_tracer()
        req = RoutingRequest(
            preferred_model="gpt-4",
            policy=RoutingPolicy.STRICT,
            fallback_strategy=FallbackStrategy.NONE,
            trace=tracer,
            request_id="trace-1",
        )
        result = asyncio.run(router.route(req))
        assert result is not None
        assert result.model_id == "gpt-4"

    @pytest.mark.asyncio
    async def test_chat_with_fallback_success(self):
        router = MultiModelRouter()
        tracer = _make_tracer()
        req = RoutingRequest(
            user_id=1,
            trace=tracer,
            request_id="trace-1",
        )
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "hello"
        mock_response.metadata = {}
        mock_provider.chat = AsyncMock(return_value=mock_response)
        with patch("app.model_router_v2.ProviderFactory.get_for_model", return_value=mock_provider):
            with patch("app.model_router_v2.MultiModelRouter.route", return_value=RoutingResult(
                model_id="gpt-4",
                provider_name="openai",
                reason="test",
                fallback_chain=[],
                estimated_cost_usd=0.01,
                estimated_latency_ms=1000,
                confidence=0.9,
            )):
                from app.providers.base import ChatMessage
                result = await router.chat_with_fallback(
                    req,
                    messages=[ChatMessage(role="user", content="hi")],
                )
                assert result.content == "hello"


class TestRoutingRequest:
    def test_defaults(self):
        req = RoutingRequest()
        assert req.policy == RoutingPolicy.BALANCED
        assert req.fallback_strategy == FallbackStrategy.CROSS_PROVIDER
        assert req.capabilities == []
        assert req.requires_function_calling is True


class TestRoutingResult:
    def test_creation(self):
        result = RoutingResult(
            model_id="gpt-4",
            provider_name="openai",
            reason="quality",
            fallback_chain=["gpt-4-turbo"],
            estimated_cost_usd=0.01,
            estimated_latency_ms=1200,
            confidence=0.9,
            metadata={"supports_streaming": True},
        )
        assert result.model_id == "gpt-4"
        assert result.fallback_chain == ["gpt-4-turbo"]
