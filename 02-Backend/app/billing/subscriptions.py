"""Subscription management."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class SubscriptionStatus(Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class SubscriptionPlan(Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class Subscription:
    subscription_id: str
    user_id: str
    plan: SubscriptionPlan
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SubscriptionManager:
    _subscriptions: Dict[str, Subscription] = {}

    @classmethod
    def create_subscription(cls, user_id: str, plan: SubscriptionPlan) -> Subscription:
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        sub_id = f"sub_{user_id}_{len(cls._subscriptions)}"
        subscription = Subscription(
            subscription_id=sub_id,
            user_id=user_id,
            plan=plan,
            status=SubscriptionStatus.TRIALING,
            current_period_start=now,
            current_period_end=period_end,
        )
        cls._subscriptions[sub_id] = subscription
        return subscription

    @classmethod
    def get_subscription(cls, user_id: str) -> Optional[Subscription]:
        for sub in cls._subscriptions.values():
            if sub.user_id == user_id:
                return sub
        return None

    @classmethod
    def cancel(cls, subscription_id: str) -> bool:
        sub = cls._subscriptions.get(subscription_id)
        if sub:
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancel_at_period_end = True
            return True
        return False
