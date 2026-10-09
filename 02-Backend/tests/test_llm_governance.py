"""Tests for the LLM governance service."""

from __future__ import annotations

import pytest
import asyncio

from app.services.llm_governance import LLMGovernanceService, ReasoningPolicy
from app.model_router_v2 import RoutingRequest, RoutingPolicy, RoutingResult, FallbackStrategy


@pytest.fixture
def service():
    return LLMGovernanceService()


class TestLLMGovernanceService:
    def test_route_returns_result(self, service):
        route_request = RoutingRequest(
            user_id=1,
            task_type="general_chat",
            policy=RoutingPolicy.BALANCED,
        )
        result = asyncio.run(service.route(route_request))
        assert "model_id" in result
        assert "provider_name" in result
        assert "fallback_chain" in result

    def test_compress_returns_result(self, service):
        from app.services.llm_governance import CompressRequest
        compress_request = CompressRequest(
            context="hello world " * 1000,
            max_tokens=100,
            query="hello",
        )
        result = asyncio.run(service.compress(compress_request))
        assert "compressed" in result
        assert "original_tokens" in result
        assert "compressed_tokens" in result

    def test_correct_returns_result(self, service):
        from app.services.llm_governance import CorrectRequest
        correct_request = CorrectRequest(
            response="hello world " * 100,
            context="hello",
        )
        result = asyncio.run(service.correct(correct_request))
        assert "original" in result
        assert "corrected" in result
        assert "issues" in result

    def test_process_returns_result(self, service):
        result = asyncio.run(service.process(
            user_message="hello",
            user_id=1,
            reasoning_policy=ReasoningPolicy.BALANCED,
        ))
        assert "request_id" in result
        assert "model_used" in result
        assert "trace" in result

    def test_reasoning_policies(self, service):
        for policy in ReasoningPolicy:
            result = asyncio.run(service.process(
                user_message="hello",
                reasoning_policy=policy,
            ))
            assert "reasoning_steps" in result
