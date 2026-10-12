"""Tests for the embeddings spend gate (backlog item 5).

The spend cap added in app/ai_spend_cap.py was wired into /chat/message
only. Embeddings, agents and RAG synthesis record nothing, so an account
that stops using chat and starts using search is unbounded.

These tests cover the embedding pricing model, which chat's price table
does not express: embeddings are billed per input token only, with no
output, so a chat-shaped table over-bills them.
"""
from __future__ import annotations

import asyncio

import pytest

from app import embedding_spend
from app.ai_spend_cap import SpendCap, SpendLimits, SpendLedger
from app.embeddings import EmbeddingService


class _FakeProvider:
    """Stand-in for a configured provider; records what it was given."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    @property
    def is_configured(self) -> bool:
        return True

    async def embed(self, texts, model=None):
        self.calls.append(list(texts))
        return [object() for _ in texts]


@pytest.fixture()
def service() -> EmbeddingService:
    s = EmbeddingService.__new__(EmbeddingService)
    s._provider = _FakeProvider()
    s._model = "text-embedding-3-small"
    return s


@pytest.fixture()
def cap(tmp_path):
    return SpendCap(ledger=SpendLedger(
        db_path=str(tmp_path / "s.db"),
        limits=SpendLimits(user_daily_usd=0.001, tenant_daily_usd=1.0),
    ))


def test_embedding_pricing_has_no_output_component():
    """An embedding call has no output tokens, so its price is input only."""
    cost = embedding_spend.estimate_embedding_cost("text-embedding-3-small", 1000)
    assert cost > 0
    # Doubling tokens must double cost, with no output term distorting it.
    assert embedding_spend.estimate_embedding_cost(
        "text-embedding-3-small", 2000
    ) == pytest.approx(cost * 2)


def test_unknown_embedding_model_is_not_free():
    """An unlisted model must price at the fallback, not zero."""
    unknown = embedding_spend.estimate_embedding_cost("model-i-never-saw", 10000)
    cheapest = min(
        embedding_spend.estimate_embedding_cost(m, 10000)
        for m in embedding_spend.EMBEDDING_PRICING_PER_1K
    )
    assert unknown >= cheapest, "an unlisted model priced below the cheapest known"


def test_token_estimate_scales_with_text(cap):
    small = embedding_spend.estimate_embedding_tokens(["hello"])
    large = embedding_spend.estimate_embedding_tokens(["hello " * 5000])
    assert large > small


def test_a_batch_over_the_limit_is_refused_before_any_spend(cap):
    """The batch limit lives in EmbeddingService.embed, not in authorize.

    It is enforced there so the caller gets a plain ValueError rather than
    a 429, which would misreport a size problem as a budget problem.
    """
    from app.embeddings import MAX_BATCH

    texts = ["chunk"] * (MAX_BATCH + 1)
    service = EmbeddingService.__new__(EmbeddingService)
    service._provider = _FakeProvider()
    service._model = "text-embedding-3-small"
    with pytest.raises(ValueError, match="exceeds the limit"):
        asyncio.run(service.embed(texts))
    assert cap._ledger.usage("u1", "t1") == 0.0


def test_a_batch_that_would_breach_the_cap_is_refused(cap):
    """A large batch against a small daily budget must not reach the provider."""
    from fastapi import HTTPException

    # 20MB of text against a $0.001 budget.
    texts = ["x" * 8000] * 100
    with pytest.raises(HTTPException):
        embedding_spend.authorize(cap, "u1", "t1", "text-embedding-3-large", texts)


def test_a_refused_batch_records_nothing(cap, tmp_path):
    from fastapi import HTTPException

    ledger = cap._ledger
    texts = ["x" * 8000] * 100
    try:
        embedding_spend.authorize(cap, "u1", "t1", "text-embedding-3-large", texts)
    except HTTPException:
        pass
    assert ledger.usage("u1", "t1") == 0.0, "a refused batch was still billed"


def test_a_small_batch_is_allowed_and_records(cap):
    embedding_spend.authorize(cap, "u1", "t1", "text-embedding-3-small", ["hi"])
    embedding_spend.record(cap, "u1", "t1", "text-embedding-3-small", ["hi"])
    assert cap._ledger.usage("u1", "t1") > 0


def test_tenants_do_not_share_the_embedding_budget(cap):
    embedding_spend.record(cap, "u1", "t1", "text-embedding-3-small", ["a" * 4000])
    assert cap._ledger.tenant_usage("t1") > 0
    assert cap._ledger.tenant_usage("t2") == 0.0


def test_record_never_raises(cap, monkeypatch):
    """Metering failure must not break the embedding request."""

    def boom(*a, **k):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(cap, "record", boom)
    # record() catches its own exception.
    embedding_spend.record(cap, "u1", "t1", "text-embedding-3-small", ["hi"])
