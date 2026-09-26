"""Subscription lifecycle management."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

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
        self._subscriptions: Dict[str, Subscription] = {}

    def create_subscription(self, org_id: str, plan: str, seats: int = 1, interval: str = "monthly") -> Subscription:
        sub_id = str(uuid.uuid4())
        subscription = Subscription(
            id=sub_id,
            org_id=org_id,
            plan=plan,
            status="active",
            interval=interval,
            seats=seats,
        )
        self._subscriptions[sub_id] = subscription
        logger.info("Created subscription %s for org %s plan %s", sub_id, org_id, plan)
        return subscription

    def upgrade_plan(self, subscription_id: str, new_plan: str) -> Subscription:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        subscription.plan = new_plan
        subscription.status = "active"
        logger.info("Upgraded subscription %s to plan %s", subscription_id, new_plan)
        return subscription

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Subscription:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        subscription.cancel_at_period_end = at_period_end
        if not at_period_end:
            subscription.status = "canceled"
        logger.info("Canceled subscription %s at_period_end=%s", subscription_id, at_period_end)
        return subscription

    def get_active_subscription(self, org_id: str) -> Optional[Subscription]:
        for sub in self._subscriptions.values():
            if sub.org_id == org_id and sub.status == "active":
                return sub
        return None

    def list_subscriptions(self, org_id: str) -> List[dict]:
        return [
            {
                "id": sub.id,
                "org_id": sub.org_id,
                "plan": sub.plan,
                "status": sub.status,
                "interval": sub.interval,
                "seats": sub.seats,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created_at": sub.created_at,
            }
            for sub in self._subscriptions.values()
            if sub.org_id == org_id
        ]


subscription_manager = SubscriptionManager()
