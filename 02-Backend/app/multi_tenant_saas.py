"""Enhanced multi-tenant SaaS platform."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TenantPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    DELETED = "deleted"


@dataclass
class Tenant:
    tenant_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    plan: TenantPlan = TenantPlan.FREE
    status: TenantStatus = TenantStatus.TRIAL
    owner_id: str = ""
    members: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    trial_ends_at: Optional[float] = None


@dataclass
class TenantQuota:
    api_calls_limit: int = 1000
    api_calls_used: int = 0
    storage_mb_limit: int = 100
    storage_mb_used: float = 0.0
    seats_limit: int = 1
    seats_used: int = 0


class MultiTenantSaaS:
    """Multi-tenant SaaS platform with isolation and quotas."""

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._quotas: Dict[str, TenantQuota] = {}
        self._domains: Dict[str, str] = {}

    def create_tenant(self, name: str, owner_id: str, plan: TenantPlan = TenantPlan.FREE) -> Tenant:
        slug = name.lower().replace(" ", "-")[:50]
        tenant = Tenant(name=name, slug=slug, owner_id=owner_id, plan=plan, members=[owner_id])
        self._tenants[tenant.tenant_id] = tenant
        self._quotas[tenant.tenant_id] = TenantQuota()
        logger.info("Created tenant %s (plan=%s)", name, plan.value)
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        for tenant in self._tenants.values():
            if tenant.slug == slug:
                return tenant
        return None

    def add_member(self, tenant_id: str, user_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant or user_id in tenant.members:
            return False
        tenant.members.append(user_id)
        return True

    def remove_member(self, tenant_id: str, user_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        if user_id in tenant.members:
            tenant.members.remove(user_id)
            return True
        return False

    def update_plan(self, tenant_id: str, plan: TenantPlan) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.plan = plan
        limits = {
            TenantPlan.FREE: {"api_calls": 1000, "storage_mb": 100, "seats": 1},
            TenantPlan.PRO: {"api_calls": 100000, "storage_mb": 5000, "seats": 10},
            TenantPlan.ENTERPRISE: {"api_calls": 1000000, "storage_mb": 50000, "seats": 100},
        }
        tenant.resource_limits = limits.get(plan, limits[TenantPlan.FREE])
        return True

    def check_quota(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        quota = self._quotas.get(tenant_id)
        if not quota:
            return False
        if resource == "api_calls":
            return quota.api_calls_used + amount <= quota.api_calls_limit
        if resource == "storage_mb":
            return quota.storage_mb_used + amount <= quota.storage_mb_limit
        if resource == "seats":
            return quota.seats_used + amount <= quota.seats_limit
        return True

    def consume_quota(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        if not self.check_quota(tenant_id, resource, amount):
            return False
        quota = self._quotas.get(tenant_id)
        if not quota:
            return False
        if resource == "api_calls":
            quota.api_calls_used += amount
        elif resource == "storage_mb":
            quota.storage_mb_used += amount
        elif resource == "seats":
            quota.seats_used += amount
        return True

    def get_quota_status(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        quota = self._quotas.get(tenant_id)
        if not quota:
            return None
        return {
            "api_calls": {"used": quota.api_calls_used, "limit": quota.api_calls_limit, "pct": round(quota.api_calls_used / max(quota.api_calls_limit, 1) * 100, 1)},
            "storage_mb": {"used": quota.storage_mb_used, "limit": quota.storage_mb_limit, "pct": round(quota.storage_mb_used / max(quota.storage_mb_limit, 1) * 100, 1)},
            "seats": {"used": quota.seats_used, "limit": quota.seats_limit, "pct": round(quota.seats_used / max(quota.seats_limit, 1) * 100, 1)},
        }


multi_tenant_saas = MultiTenantSaaS()
