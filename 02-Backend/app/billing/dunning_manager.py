"""Dunning management for failed payments."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class DunningStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class DunningAttempt:
    attempt_id: str
    user_id: str
    invoice_id: str
    attempt_number: int
    amount: float
    status: str
    error: Optional[str] = None
    attempted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DunningPolicy:
    policy_id: str
    max_attempts: int = 3
    retry_delays: List[int] = field(default_factory=lambda: [3, 7, 14])
    grace_period_days: int = 7
    suspend_after_days: int = 14
    email_notifications: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DunningManager:
    _attempts: Dict[str, List[DunningAttempt]] = {}
    _policies: Dict[str, DunningPolicy] = {}
    _active_dunning: Dict[str, DunningAttempt] = {}

    @classmethod
    def register_policy(cls, policy: DunningPolicy) -> None:
        cls._policies[policy.policy_id] = policy

    @classmethod
    def start_dunning(cls, user_id: str, invoice_id: str, amount: float) -> str:
        policy = list(cls._policies.values())[0] if cls._policies else DunningPolicy(policy_id="default")
        attempt_id = f"dunning_{user_id}_{datetime.now(timezone.utc).timestamp()}"
        attempt = DunningAttempt(
            attempt_id=attempt_id,
            user_id=user_id,
            invoice_id=invoice_id,
            attempt_number=1,
            amount=amount,
            status="pending",
        )
        if user_id not in cls._attempts:
            cls._attempts[user_id] = []
        cls._attempts[user_id].append(attempt)
        cls._active_dunning[user_id] = attempt
        return attempt_id

    @classmethod
    def record_failure(cls, user_id: str, error: str) -> Optional[DunningAttempt]:
        attempt = cls._active_dunning.get(user_id)
        if attempt:
            attempt.status = "failed"
            attempt.error = error
        return attempt

    @classmethod
    def get_active_dunning(cls, user_id: str) -> Optional[DunningAttempt]:
        return cls._active_dunning.get(user_id)
