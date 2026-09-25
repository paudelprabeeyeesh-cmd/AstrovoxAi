"""
Usage and cost tracking with billing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    user_id: str
    request_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class CostCalculator:
    """Calculate costs for different models and operations."""

    PRICING = {
        "astrovox-1b": {"prompt": 0.0001, "completion": 0.0002},
        "astrovox-7b": {"prompt": 0.0005, "completion": 0.001},
        "astrovox-70b": {"prompt": 0.002, "completion": 0.004},
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
        "gemini-pro": {"prompt": 0.0005, "completion": 0.0015},
    }

    @classmethod
    def calculate(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = cls.PRICING.get(model, {"prompt": 0.001, "completion": 0.002})
        return (pricing["prompt"] * prompt_tokens + pricing["completion"] * completion_tokens) / 1000


class UsageTracker:
    """Track usage and costs per user."""

    def __init__(self):
        self.records: List[UsageRecord] = []
        self.user_quotas: Dict[str, float] = {}
        self.user_spending: Dict[str, float] = {}

    def record_usage(self, record: UsageRecord):
        self.records.append(record)
        self.user_spending[record.user_id] = self.user_spending.get(record.user_id, 0.0) + record.cost_usd

    def check_quota(self, user_id: str) -> bool:
        quota = self.user_quotas.get(user_id, float("inf"))
        spent = self.user_spending.get(user_id, 0.0)
        return spent < quota

    def get_user_stats(self, user_id: str) -> dict:
        user_records = [r for r in self.records if r.user_id == user_id]
        total_cost = sum(r.cost_usd for r in user_records)
        total_tokens = sum(r.total_tokens for r in user_records)
        return {
            "total_requests": len(user_records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(sum(r.latency_ms for r in user_records) / max(len(user_records), 1), 2),
            "quota_remaining": round(self.user_quotas.get(user_id, float("inf")) - self.user_spending.get(user_id, 0.0), 4),
        }

    def get_global_stats(self) -> dict:
        total_cost = sum(r.cost_usd for r in self.records)
        total_tokens = sum(r.total_tokens for r in self.records)
        return {
            "total_requests": len(self.records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "unique_users": len(set(r.user_id for r in self.records)),
        }
