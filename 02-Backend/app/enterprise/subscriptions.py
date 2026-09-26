"""Subscription lifecycle management."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    id: str
    org_id: str
    plan: str
    status: str
    interval: str
    seats: int
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SubscriptionManager:
    def __init__(self):
        self._subscriptions: dict[str, Subscription] = {}

    def create_subscription(self, org_id: str, plan: str, seats: int = 1, interval: str = "monthly") -> Subscription:
        sub_id = str(uuid.uuid4())
        subscription = Subscription(id=sub_id, org_id=org_id, plan=plan, status="active", interval=interval, seats=seats)
        self._subscriptions[sub_id] = subscription
        self._persist(subscription)
        return subscription

    def _persist(self, subscription: Subscription):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO subscriptions (id, org_id, plan, status, interval, seats, current_period_end, cancel_at_period_end, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    subscription.id,
                    subscription.org_id,
                    subscription.plan,
                    subscription.status,
                    subscription.interval,
                    subscription.seats,
                    subscription.current_period_end,
                    1 if subscription.cancel_at_period_end else 0,
                    subscription.created_at,
                ),
            )
            conn.commit()

    def upgrade_plan(self, subscription_id: str, new_plan: str) -> Subscription:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        subscription.plan = new_plan
        subscription.status = "active"
        self._persist(subscription)
        return subscription

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Subscription:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        subscription.cancel_at_period_end = at_period_end
        if not at_period_end:
            subscription.status = "canceled"
        self._persist(subscription)
        return subscription

    def get_active_subscription(self, org_id: str) -> Optional[Subscription]:
        for sub in self._subscriptions.values():
            if sub.org_id == org_id and sub.status == "active":
                return sub
        return None


subscription_manager = SubscriptionManager()
