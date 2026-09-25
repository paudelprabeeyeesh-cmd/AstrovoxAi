"""Quota manager for subscription limits."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class QuotaLimit(Enum):
    REQUESTS_PER_MONTH = "requests_per_month"
    TOKENS_PER_MONTH = "tokens_per_month"
    STORAGE_GB = "storage_gb"
    TEAM_MEMBERS = "team_members"
    API_KEYS = "api_keys"


@dataclass
class Quota:
    quota_id: str
    user_id: str
    plan: str
    limits: Dict[QuotaLimit, int] = field(default_factory=dict)
    usage: Dict[QuotaLimit, int] = field(default_factory=dict)
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))

    def is_exceeded(self, limit: QuotaLimit) -> bool:
        return self.usage.get(limit, 0) >= self.limits.get(limit, 0)

    def remaining(self, limit: QuotaLimit) -> int:
        return max(0, self.limits.get(limit, 0) - self.usage.get(limit, 0))


class QuotaManager:
    _quotas: Dict[str, Quota] = {}

    PLAN_LIMITS = {
        "free": {
            QuotaLimit.REQUESTS_PER_MONTH: 100,
            QuotaLimit.TOKENS_PER_MONTH: 10000,
            QuotaLimit.STORAGE_GB: 1,
        },
        "basic": {
            QuotaLimit.REQUESTS_PER_MONTH: 10000,
            QuotaLimit.TOKENS_PER_MONTH: 500000,
            QuotaLimit.STORAGE_GB: 10,
        },
        "pro": {
            QuotaLimit.REQUESTS_PER_MONTH: 100000,
            QuotaLimit.TOKENS_PER_MONTH: 5000000,
            QuotaLimit.STORAGE_GB: 100,
        },
        "enterprise": {
            QuotaLimit.REQUESTS_PER_MONTH: 1000000,
            QuotaLimit.TOKENS_PER_MONTH: 50000000,
            QuotaLimit.STORAGE_GB: 1000,
        },
    }

    @classmethod
    def create_quota(cls, user_id: str, plan: str) -> Quota:
        quota_id = f"quota_{user_id}"
        limits = cls.PLAN_LIMITS.get(plan, cls.PLAN_LIMITS["free"])
        quota = Quota(quota_id=quota_id, user_id=user_id, plan=plan, limits=limits)
        cls._quotas[quota_id] = quota
        return quota

    @classmethod
    def consume(cls, user_id: str, limit: QuotaLimit, amount: int = 1) -> bool:
        quota_id = f"quota_{user_id}"
        quota = cls._quotas.get(quota_id)
        if not quota or quota.is_exceeded(limit):
            return False
        quota.usage[limit] = quota.usage.get(limit, 0) + amount
        return True

    @classmethod
    def get_quota(cls, user_id: str) -> Optional[Quota]:
        return cls._quotas.get(f"quota_{user_id}")
