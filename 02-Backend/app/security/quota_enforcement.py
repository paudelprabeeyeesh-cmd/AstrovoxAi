"""Quota enforcement for API usage."""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class QuotaType(Enum):
    REQUESTS = "requests"
    TOKENS = "tokens"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    COMPUTE = "compute"


@dataclass
class Quota:
    quota_id: str
    user_id: str
    quota_type: QuotaType
    limit: int
    used: int = 0
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))

    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def is_exceeded(self) -> bool:
        return self.used >= self.limit


class QuotaEnforcer:
    _quotas: Dict[str, Quota] = {}

    @classmethod
    def set_quota(cls, quota: Quota) -> None:
        cls._quotas[quota.quota_id] = quota

    @classmethod
    def get_quota(cls, quota_id: str) -> Optional[Quota]:
        return cls._quotas.get(quota_id)

    @classmethod
    def consume(cls, quota_id: str, amount: int = 1) -> bool:
        quota = cls._quotas.get(quota_id)
        if not quota or quota.is_exceeded():
            return False
        quota.used += amount
        return True

    @classmethod
    def reset_period(cls, quota_id: str) -> None:
        quota = cls._quotas.get(quota_id)
        if quota:
            quota.used = 0
            quota.period_start = datetime.now(timezone.utc)
            quota.period_end = datetime.now(timezone.utc) + timedelta(days=30)

    @classmethod
    def list_quotas(cls, user_id: str) -> List[Quota]:
        return [q for q in cls._quotas.values() if q.user_id == user_id]
