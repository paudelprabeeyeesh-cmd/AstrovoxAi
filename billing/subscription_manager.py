"""
Subscription management for AstrovoxAI.
Handles plans, subscriptions, upgrades, downgrades, and renewals.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"


@dataclass
class Plan:
    plan_id: str
    name: str
    tier: PlanTier
    price_monthly: float
    price_yearly: float
    limits: Dict[str, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "tier": self.tier.value,
            "price_monthly": self.price_monthly,
            "price_yearly": self.price_yearly,
            "limits": self.limits,
            "features": self.features,
        }


@dataclass
class Subscription:
    subscription_id: str
    developer_id: str
    plan: Plan
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "developer_id": self.developer_id,
            "plan": self.plan.to_dict(),
            "status": self.status.value,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "cancel_at_period_end": self.cancel_at_period_end,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
        }


class SubscriptionManager:
    """Manages developer subscriptions and plan changes."""

    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._plans: Dict[str, Plan] = {}
        self._initialize_default_plans()

    def _initialize_default_plans(self) -> None:
        self._plans["free"] = Plan(
            plan_id="free",
            name="Free",
            tier=PlanTier.FREE,
            price_monthly=0.0,
            price_yearly=0.0,
            limits={"api_calls_per_month": 1000, "tokens_per_month": 100000, "projects": 1},
            features=["basic_api", "community_support"],
        )
        self._plans["starter"] = Plan(
            plan_id="starter",
            name="Starter",
            tier=PlanTier.STARTER,
            price_monthly=29.0,
            price_yearly=290.0,
            limits={"api_calls_per_month": 10000, "tokens_per_month": 1000000, "projects": 5},
            features=["basic_api", "priority_support", "analytics_dashboard"],
            stripe_price_id_monthly="price_starter_monthly",
            stripe_price_id_yearly="price_starter_yearly",
        )
        self._plans["pro"] = Plan(
            plan_id="pro",
            name="Pro",
            tier=PlanTier.PRO,
            price_monthly=99.0,
            price_yearly=990.0,
            limits={"api_calls_per_month": 100000, "tokens_per_month": 10000000, "projects": 25},
            features=["advanced_api", "priority_support", "advanced_analytics", "sso"],
            stripe_price_id_monthly="price_pro_monthly",
            stripe_price_id_yearly="price_pro_yearly",
        )
        self._plans["enterprise"] = Plan(
            plan_id="enterprise",
            name="Enterprise",
            tier=PlanTier.ENTERPRISE,
            price_monthly=499.0,
            price_yearly=4990.0,
            limits={"api_calls_per_month": -1, "tokens_per_month": -1, "projects": -1},
            features=["advanced_api", "dedicated_support", "advanced_analytics", "sso", "sla", "private_deployment"],
            stripe_price_id_monthly="price_enterprise_monthly",
            stripe_price_id_yearly="price_enterprise_yearly",
        )

    def list_plans(self) -> List[Plan]:
        return list(self._plans.values())

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def create_subscription(
        self,
        developer_id: str,
        plan_id: str,
        interval: str = "monthly",
        trial_days: int = 0,
    ) -> Subscription:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        now = datetime.utcnow()
        period_end = now + timedelta(days=30 if interval == "monthly" else 365)
        trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            developer_id=developer_id,
            plan=plan,
            status=SubscriptionStatus.TRIALING if trial_end else SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=period_end,
            trial_end=trial_end,
        )
        self._subscriptions[subscription.subscription_id] = subscription
        logger.info("Created subscription %s for developer %s", subscription.subscription_id, developer_id)
        return subscription

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        return self._subscriptions.get(subscription_id)

    def get_developer_subscription(self, developer_id: str) -> Optional[Subscription]:
        for sub in self._subscriptions.values():
            if sub.developer_id == developer_id:
                return sub
        return None

    def upgrade_subscription(self, subscription_id: str, new_plan_id: str) -> Subscription:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")
        new_plan = self._plans.get(new_plan_id)
        if not new_plan:
            raise ValueError(f"Plan {new_plan_id} not found")
        if new_plan.tier.value <= subscription.plan.tier.value:
            raise ValueError("Cannot upgrade to a lower or equal tier plan")
        subscription.plan = new_plan
        logger.info("Upgraded subscription %s to plan %s", subscription_id, new_plan_id)
        return subscription

    def cancel_subscription(self, subscription_id: str, immediate: bool = False) -> None:
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")
        if immediate:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.current_period_end = datetime.utcnow()
        else:
            subscription.cancel_at_period_end = True
        logger.info("Canceled subscription %s", subscription_id)
