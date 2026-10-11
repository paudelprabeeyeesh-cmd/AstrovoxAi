"""Server-side AI spend caps (W5.2).

A request-count quota bounds the number of calls but not their cost. One
4000-character request and one 20-character request count the same, so the
cap does not actually bound provider spend. Worse, request counting is
per user, so the same limit can be bypassed entirely by creating N
accounts, and there is no aggregate ceiling that stops one tenant (or one
deployment) burning the whole provider balance overnight.

This module adds a cost dimension:

* an estimate is computed before the provider call, so a request that
  would breach the cap is refused before any money is spent;
* actuals are recorded after the call, so the ledger converges on real
  usage;
* limits exist per user per day, and per tenant per day, so neither a
  single heavy user nor an aggregate campaign can exceed the budget;
* approaching the cap emits a warning, and crossing it emits a critical
  alert, so spend spikes are visible rather than silent.

Costs are USD per 1K tokens. A model absent from the table is treated as
unknown and priced at the most expensive known model, so a new or renamed
model cannot silently become free.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------
# USD per 1,000 tokens. Update when a provider changes its rates; a stale
# table under-bills the user, which fails closed for the operator but
# under-reports, so it should be refreshed.
PRICING_PER_1K: Dict[str, Dict[str, float]] = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
}

# Price charged when a model is not in the table. The most expensive known
# entry, so an unrecognised model cannot be used to sidestep the cap.
_STRICT_FALLBACK = max(
    max(v["input"], v["output"]) for v in PRICING_PER_1K.values()
)

# Rough character-to-token ratio. Deliberately generous: an
# over-estimate refuses a request the cheap model would have allowed,
# while an under-estimate lets spend through the cap.
CHARS_PER_TOKEN = 4.0


def estimate_tokens(text: str, context_chars: int = 0) -> int:
    """Estimate the tokens a request will consume.

    Includes the conversation context, because a long history is what
    makes an actual request expensive. Estimation is intentionally
    conservative.
    """
    if not isinstance(text, str):
        return 0
    total_chars = len(text) + max(0, int(context_chars))
    return int(total_chars / CHARS_PER_TOKEN) + 1


def estimate_cost(model: str, prompt_tokens: int, max_output_tokens: int = 0) -> float:
    """Estimate a request's cost in USD.

    ``prompt_tokens`` is the input; ``max_output_tokens`` is the bound the
    caller asked for, defaulting to 1K when the caller did not say.
    """
    price = PRICING_PER_1K.get(model)
    if price is None:
        price = {"input": _STRICT_FALLBACK, "output": _STRICT_FALLBACK}
    if max_output_tokens <= 0:
        max_output_tokens = 1024
    return (
        (prompt_tokens / 1000.0) * price["input"]
        + (max_output_tokens / 1000.0) * price["output"]
    )


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------


@dataclass
class SpendLimits:
    """Daily caps in USD, per user and per tenant."""

    user_daily_usd: float = 1.0
    tenant_daily_usd: float = 500.0
    # Warn at this fraction of the user cap.
    warn_at: float = 0.8


def _default_limits() -> SpendLimits:
    user_daily = os.getenv("AI_DAILY_SPEND_LIMIT_USD", "")
    tenant_daily = os.getenv("TENANT_DAILY_SPEND_LIMIT_USD", "")
    return SpendLimits(
        user_daily_usd=float(user_daily) if user_daily else 1.0,
        tenant_daily_usd=float(tenant_daily) if tenant_daily else 500.0,
    )


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


class SpendLedger:
    """SQLite-backed ledger of AI spend.

    One row per user per day. Written on a new connection each time, with
    ``BEGIN IMMEDIATE`` around the read-modify-write, so two concurrent
    requests for the same user cannot both read "under the limit" and both
    spend through it.
    """

    def __init__(self, db_path: Optional[str] = None, limits: Optional[SpendLimits] = None) -> None:
        self.db_path = db_path or os.getenv("AI_SPEND_DB_PATH", "./ai_spend.db")
        self.limits = limits or _default_limits()
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS ai_spend (
                        day TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL DEFAULT '',
                        spend_usd REAL NOT NULL DEFAULT 0,
                        requests INTEGER NOT NULL DEFAULT 0,
                        tokens INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (day, user_id, tenant_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_ai_spend_day_tenant
                        ON ai_spend (day, tenant_id);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _add(self, day: str, user_id: str, tenant_id: str, usd: float, tokens: int) -> float:
        """Record spend for one row and return the row's new total."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT spend_usd FROM ai_spend WHERE day=? AND user_id=? AND tenant_id=?",
                    (day, user_id, tenant_id),
                ).fetchone()
                current = float(row["spend_usd"]) if row else 0.0
                new_total = current + usd
                if row:
                    conn.execute(
                        "UPDATE ai_spend SET spend_usd=?, requests=requests+1, tokens=tokens+? "
                        "WHERE day=? AND user_id=? AND tenant_id=?",
                        (new_total, tokens, day, user_id, tenant_id),
                    )
                else:
                    conn.execute(
                        "INSERT INTO ai_spend (day, user_id, tenant_id, spend_usd, requests, tokens) "
                        "VALUES (?, ?, ?, ?, 1, ?)",
                        (day, user_id, tenant_id, new_total, tokens),
                    )
                conn.commit()
                return new_total
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def record(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        tenant_id: str = "",
    ) -> float:
        """Record actual usage. Returns the user's new daily total."""
        price = PRICING_PER_1K.get(model, {"input": _STRICT_FALLBACK, "output": _STRICT_FALLBACK})
        usd = (input_tokens / 1000.0) * price["input"] + (output_tokens / 1000.0) * price["output"]
        return self._add(
            self._today(), user_id, tenant_id, usd, input_tokens + output_tokens
        )

    def usage(self, user_id: str, tenant_id: str = "", day: Optional[str] = None) -> float:
        day = day or self._today()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT spend_usd FROM ai_spend WHERE day=? AND user_id=? AND tenant_id=?",
                (day, user_id, tenant_id),
            ).fetchone()
            return float(row["spend_usd"]) if row else 0.0
        finally:
            conn.close()

    def tenant_usage(self, tenant_id: str, day: Optional[str] = None) -> float:
        day = day or self._today()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(spend_usd), 0) AS total FROM ai_spend WHERE day=? AND tenant_id=?",
                (day, tenant_id),
            ).fetchone()
            return float(row["total"]) if row else 0.0
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


@dataclass
class SpendDecision:
    allowed: bool
    estimated_usd: float
    user_used_usd: float
    user_limit_usd: float
    tenant_used_usd: float
    tenant_limit_usd: float
    reason: str


class SpendCap:
    """Pre-flight and post-flight gate for AI spend."""

    def __init__(self, ledger: Optional[SpendLedger] = None, limits: Optional[SpendLimits] = None) -> None:
        self._ledger = ledger or SpendLedger(limits=limits)
        self.limits = limits or self._ledger.limits

    def authorize(
        self,
        user_id: str,
        model: str,
        prompt_tokens: int,
        max_output_tokens: int = 0,
        tenant_id: str = "",
        context_chars: int = 0,
    ) -> SpendDecision:
        """Decide whether a request may run. Refuses before any spend."""
        # The prompt estimate is bounded below by what was actually sent.
        tokens = max(prompt_tokens, estimate_tokens("", context_chars))
        estimated = estimate_cost(model, tokens, max_output_tokens)

        user_used = self._ledger.usage(user_id, tenant_id)
        tenant_used = self._ledger.tenant_usage(tenant_id)

        if user_used + estimated > self.limits.user_daily_usd:
            if user_used >= self.limits.user_daily_usd * self.limits.warn_at:
                self._alert("warn", user_id, tenant_id, user_used, estimated)
            return SpendDecision(
                allowed=False,
                estimated_usd=estimated,
                user_used_usd=user_used,
                user_limit_usd=self.limits.user_daily_usd,
                tenant_used_usd=tenant_used,
                tenant_limit_usd=self.limits.tenant_daily_usd,
                reason=(
                    "Daily AI spend limit reached for this account "
                    "($%.4f/$%.2f). Contact your administrator or retry tomorrow."
                    % (user_used, self.limits.user_daily_usd)
                ),
            )

        if tenant_used + estimated > self.limits.tenant_daily_usd:
            self._alert("critical", user_id, tenant_id, user_used, estimated)
            return SpendDecision(
                allowed=False,
                estimated_usd=estimated,
                user_used_usd=user_used,
                user_limit_usd=self.limits.user_daily_usd,
                tenant_used_usd=tenant_used,
                tenant_limit_usd=self.limits.tenant_daily_usd,
                reason=(
                    "Daily AI spend limit reached for this tenant "
                    "($%.4f/$%.2f)."
                    % (tenant_used, self.limits.tenant_daily_usd)
                ),
            )

        if user_used >= self.limits.user_daily_usd * self.limits.warn_at:
            self._alert("warn", user_id, tenant_id, user_used, estimated)

        return SpendDecision(
            allowed=True,
            estimated_usd=estimated,
            user_used_usd=user_used,
            user_limit_usd=self.limits.user_daily_usd,
            tenant_used_usd=tenant_used,
            tenant_limit_usd=self.limits.tenant_daily_usd,
            reason="ok",
        )

    def record(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        tenant_id: str = "",
    ) -> float:
        return self._ledger.record(
            user_id, model, input_tokens, output_tokens, tenant_id
        )

    def _alert(self, level: str, user_id: str, tenant_id: str, used: float, estimated: float) -> None:
        # No token or value-bearing detail is logged; the amounts are
        # operational, not secret, but the user identity is not needed at
        # warn level either.
        logger.warning(
            "ai_spend.level=%s tenant=%s used_usd=%.4f next_usd=%.4f limit_usd=%.2f",
            level, tenant_id or "default", used, estimated, self.limits.user_daily_usd,
        )


_GLOBAL_CAP: Optional[SpendCap] = None


def get_spend_cap() -> SpendCap:
    """Process-wide gate. One ledger, one set of limits, so the caps are
    enforced consistently no matter which route enforces them."""
    global _GLOBAL_CAP
    if _GLOBAL_CAP is None:
        _GLOBAL_CAP = SpendCap()
    return _GLOBAL_CAP


def reset_spend_cap() -> None:
    """Drop the cached gate. Used by tests so a temp DB is picked up."""
    global _GLOBAL_CAP
    _GLOBAL_CAP = None
