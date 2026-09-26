"""Multi-tenant middleware and data isolation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Tenant:
    tenant_id: str
    name: str
    plan: str
    quota: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TenantIsolator:
    def __init__(self) -> None:
        self._tenants: Dict[str, Tenant] = {}
        self._tenant_context: Dict[str, str] = {}

    def register_tenant(self, tenant: Tenant) -> None:
        self._tenants[tenant.tenant_id] = tenant
        logger.info("Registered tenant %s: %s", tenant.tenant_id, tenant.name)

    def set_context(self, tenant_id: str) -> None:
        if tenant_id not in self._tenants:
            raise ValueError(f"Unknown tenant: {tenant_id}")
        self._tenant_context["current"] = tenant_id

    def get_current_tenant(self) -> Optional[str]:
        return self._tenant_context.get("current")

    def filter_by_tenant(self, query: Dict[str, Any], tenant_field: str = "tenant_id") -> Dict[str, Any]:
        current = self.get_current_tenant()
        if not current:
            return query
        query.setdefault("where", []).append({tenant_field: current})
        return query

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def enforce_quota(self, tenant_id: str, resource: str, amount: int = 1) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        quota = tenant.quota.get(resource)
        if quota is None:
            return True
        return quota >= amount


tenant_isolator = TenantIsolator()
