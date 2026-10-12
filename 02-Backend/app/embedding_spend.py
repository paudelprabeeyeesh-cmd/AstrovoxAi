"""Spend gating for the embeddings path (backlog item 5).

The spend cap added in app/ai_spend_cap.py was wired into
/chat/message only. Embeddings, agents and RAG synthesis still record
nothing, so the cap is conservative rather than complete: an account that
stops using chat and starts using search instead is unbounded.

This wraps the embedding call with the same gate, and adds the pricing
model that was missing: embeddings are billed per input token only, with
no output, which chat.pricing does not express.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.ai_spend_cap import SpendCap, get_spend_cap  # noqa: F401

logger = logging.getLogger(__name__)

# USD per 1,000 input tokens. Embedding models have no output tokens, so a
# chat-shaped table over-bills them and a missing entry under-bills.
EMBEDDING_PRICING_PER_1K = {
    "models/embedding-001": 0.0000125,
    "text-embedding-004": 0.0000125,
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
}

# Charged when a model is not in the table, so an unrecognised model cannot
# be free inference.
EMBEDDING_FALLBACK = max(EMBEDDING_PRICING_PER_1K.values())

# Gemini caps a batch at 100 texts; a larger batch is rejected, and a caller
# sending 10,000 rows would fail before spending. The cap is the point.
MAX_BATCH = 100


def estimate_embedding_tokens(texts: list[str]) -> int:
    """Estimate tokens for a batch, sized by total characters."""
    return sum(len(t) for t in texts if isinstance(t, str)) // 4 + len(texts)


def estimate_embedding_cost(model: str, tokens: int) -> float:
    price = EMBEDDING_PRICING_PER_1K.get(model, EMBEDDING_FALLBACK)
    return (tokens / 1000.0) * price


def authorize(
    cap: Optional[SpendCap],
    user_id: str,
    tenant_id: str,
    model: str,
    texts: list[str],
) -> None:
    """Refuse a batch that would breach the user's daily spend.

    Raises on refusal so the caller cannot accidentally proceed.

    The decision is made here rather than by delegating to
    ``SpendCap.authorize``. That path prices with the chat table, where an
    embedding model is absent and therefore billed at the most expensive
    chat rate: every embedding request would be refused. Embeddings are
    input-only, so they need their own arithmetic.
    """
    if cap is None:
        cap = get_spend_cap()
    limits = cap.limits
    tokens = estimate_embedding_tokens(texts)
    cost = estimate_embedding_cost(model, tokens)

    user_used = cap._ledger.usage(user_id, tenant_id)
    tenant_used = cap._ledger.tenant_usage(tenant_id)

    if user_used + cost > limits.user_daily_usd:
        logger.warning(
            "spend.embedding_refused user tenant=%s used_usd=%.6f next_usd=%.6f limit_usd=%.4f",
            tenant_id or "default", user_used, cost, limits.user_daily_usd,
        )
        raise _refused(
            "Daily AI spend limit reached for this account "
            "($%.4f/$%.2f). Contact your administrator or retry tomorrow."
            % (user_used, limits.user_daily_usd)
        )

    if tenant_used + cost > limits.tenant_daily_usd:
        logger.warning(
            "spend.embedding_refused tenant=%s used_usd=%.6f next_usd=%.6f limit_usd=%.4f",
            tenant_id or "default", tenant_used, cost, limits.tenant_daily_usd,
        )
        raise _refused(
            "Daily AI spend limit reached for this tenant "
            "($%.4f/$%.2f)." % (tenant_used, limits.tenant_daily_usd)
        )


def _refused(detail: str):
    """Build the 429. Imported lazily so the module stays importable in a
    context that has not installed FastAPI (the unit tests)."""
    from fastapi import HTTPException

    return HTTPException(status_code=429, detail=detail)


def record(
    cap: Optional[SpendCap],
    user_id: str,
    tenant_id: str,
    model: str,
    texts: list[str],
) -> None:
    """Record the actual tokens consumed. Never breaks the caller."""
    if cap is None:
        cap = get_spend_cap()
    try:
        cap.record(
            user_id, model,
            estimate_embedding_tokens(texts), 0,
            tenant_id,
        )
    except Exception:  # noqa: BLE001 - metering must not fail the request
        logger.exception("spend.embedding_record_failed")
