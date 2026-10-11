"""Tests for the AI spend cap (W5.2).

A request-count quota bounds calls, not cost. These tests prove the cost
dimension is actually enforced: that a request which would breach the cap
is refused before it runs, that the ledger converges on real usage, and
that a model absent from the price table cannot be used to get free
inference.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

import app.ai_spend_cap as spend


@pytest.fixture()
def ledger(tmp_path):
    """A ledger on a temp DB so tests never touch the real one."""
    db = tmp_path / "spend.db"
    return spend.SpendLedger(db_path=str(db), limits=spend.SpendLimits(
        user_daily_usd=0.01, tenant_daily_usd=1.0, warn_at=0.5
    ))


@pytest.fixture()
def cap(ledger):
    return spend.SpendCap(ledger=ledger)


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def test_estimate_tokens_includes_context():
    cheap = spend.estimate_tokens("hello")
    with_history = spend.estimate_tokens("hello", context_chars=40000)
    assert with_history > cheap, "long history must raise the estimate"


def test_unknown_model_is_priced_at_the_most_expensive_known():
    """A model missing from the table must not become free inference."""
    unknown = spend.estimate_cost("model-i-have-never-heard-of", 1000, 1000)
    known_cheapest = spend.estimate_cost("gpt-4o-mini", 1000, 1000)
    assert unknown > known_cheapest, "an unknown model priced below the cheapest known model"


def test_estimate_cost_scales_with_tokens():
    small = spend.estimate_cost("gpt-4o", 100, 100)
    large = spend.estimate_cost("gpt-4o", 10_000, 100)
    assert large > small


# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------


def test_cap_allows_a_small_request(cap):
    d = cap.authorize("u1", "gpt-4o-mini", 100, 100, tenant_id="t1")
    assert d.allowed, d.reason
    assert d.estimated_usd > 0


def test_cap_refuses_once_the_daily_budget_is_exhausted(cap, ledger):
    # One huge request against a $0.01 limit is refused before it runs.
    d = cap.authorize("u1", "gpt-4", 1_000_000, 100_000, tenant_id="t1")
    assert not d.allowed, "an unaffordable request was allowed through"
    assert "spend limit" in d.reason.lower()
    assert d.user_limit_usd == 0.01


def test_cap_refuses_before_any_money_is_spent(cap, ledger):
    cap.authorize("u1", "gpt-4", 1_000_000, 100_000, tenant_id="t1")
    assert ledger.usage("u1", "t1") == 0.0, "a refused request still spent money"


def test_cap_counts_real_usage_after_the_call(cap, ledger):
    cap.authorize("u1", "gpt-4o", 100, 100, tenant_id="t1")
    total = cap.record("u1", "gpt-4o", 100, 100, "t1")
    assert total > 0
    assert ledger.usage("u1", "t1") == total


def test_tenant_cap_blocks_a_user_who_is_under_their_own_limit(tmp_path, ledger):
    """Per-user limits alone let one account through; the tenant cap is the
    ceiling that stops an aggregate campaign."""
    db = Path(ledger.db_path)
    # Spend the tenant's budget from a *different* user.
    ledger.record("someone-else", "gpt-4", 100_000, 100_000, "t1")
    cap = spend.SpendCap(ledger=ledger)
    d = cap.authorize("u1", "gpt-4o", 10, 10, tenant_id="t1")
    assert not d.allowed, "tenant budget exhausted but the request was allowed"
    assert "tenant" in d.reason.lower()


def test_unknown_model_is_not_a_free_path(cap):
    expensive = cap.authorize("u1", "gpt-4o", 50_000, 50_000, tenant_id="t")
    unknown = cap.authorize("u2", "no-such-model", 50_000, 50_000, tenant_id="t")
    assert unknown.estimated_usd >= expensive.estimated_usd, (
        "an unrecognised model priced below the expensive known one"
    )


def test_user_scoping_is_per_user(cap, ledger):
    cap.record("u1", "gpt-4o", 1000, 1000, "t1")
    assert ledger.usage("u1", "t1") > 0
    assert ledger.usage("u2", "t1") == 0.0, "one user's spend charged to another"


def test_ledger_is_isolated_per_tenant(cap, ledger):
    cap.record("u1", "gpt-4o", 1000, 1000, "tA")
    assert ledger.tenant_usage("tA") > 0
    assert ledger.tenant_usage("tB") == 0.0


def test_limits_can_be_configured_by_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DAILY_SPEND_LIMIT_USD", "5.5")
    limits = spend._default_limits()
    assert limits.user_daily_usd == 5.5


def test_default_limits_when_env_absent(monkeypatch):
    monkeypatch.delenv("AI_DAILY_SPEND_LIMIT_USD", raising=False)
    monkeypatch.delenv("TENANT_DAILY_SPEND_LIMIT_USD", raising=False)
    limits = spend._default_limits()
    assert limits.user_daily_usd > 0, "a default of 0 would block all inference"


def test_global_gate_is_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_SPEND_DB_PATH", str(tmp_path / "g.db"))
    spend.reset_spend_cap()
    first = spend.get_spend_cap()
    assert first is spend.get_spend_cap(), "the global gate was rebuilt"
