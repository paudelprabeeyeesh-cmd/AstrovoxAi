"""Multi-tenant hardening — tenant context, isolation, and lifecycle."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Tenant:
    id: str
    name: str
    slug: str
    domain: str = ""
    plan: str = "free"
    status: str = "active"
    owner_id: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)
    quotas: Dict[str, float] = field(default_factory=dict)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TenantManager:
    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._context: Optional[str] = None

    def create_tenant(self, name: str, domain: str, plan: str = "free", admin_email: str = "", owner_id: str = "") -> Tenant:
        tenant_id = str(uuid.uuid4())
        slug = name.lower().replace(" ", "-")[:64]
        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=slug,
            domain=domain,
            plan=plan,
            owner_id=owner_id,
        )
        self._tenants[tenant_id] = tenant
        logger.info("Created tenant %s (%s)", tenant_id, name)
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        for tenant in self._tenants.values():
            if tenant.domain == domain:
                return tenant
        return None

    def set_tenant_context(self, tenant_id: str) -> None:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            raise ValueError(f"Unknown tenant: {tenant_id}")
        if not tenant.is_active:
            raise ValueError(f"Tenant {tenant_id} is inactive")
        self._context = tenant_id
        logger.debug("Set tenant context to %s", tenant_id)

    def clear_tenant_context(self) -> None:
        self._context = None

    def get_current_tenant(self) -> Optional[Tenant]:
        if not self._context:
            return None
        return self._tenants.get(self._context)

    def require_tenant(self) -> Tenant:
        tenant = self.get_current_tenant()
        if not tenant:
            raise RuntimeError("No tenant context set")
        return tenant

    def set_quota(self, tenant_id: str, resource: str, limit: float) -> None:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            raise ValueError(f"Unknown tenant: {tenant_id}")
        tenant.quotas[resource] = limit
        logger.info("Set quota for tenant %s resource %s limit %s", tenant_id, resource, limit)

    def get_quota(self, tenant_id: str, resource: str) -> float:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return 0.0
        return tenant.quotas.get(resource, 0.0)

    def check_quota(self, tenant_id: str, resource: str, used: float) -> bool:
        limit = self.get_quota(tenant_id, resource)
        if limit <= 0:
            return True
        return used < limit

    def suspend_tenant(self, tenant_id: str) -> None:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = "suspended"
            tenant.is_active = False
            tenant.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("Suspended tenant %s", tenant_id)

    def reactivate_tenant(self, tenant_id: str) -> None:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.status = "active"
            tenant.is_active = True
            tenant.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("Reactivated tenant %s", tenant_id)

    def delete_tenant(self, tenant_id: str) -> bool:
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            if self._context == tenant_id:
                self._context = None
            logger.info("Deleted tenant %s", tenant_id)
            return True
        return False

    def list_tenants(self) -> List[dict]:
        return [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "domain": t.domain,
                "plan": t.plan,
                "status": t.status,
                "is_active": t.is_active,
                "created_at": t.created_at,
            }
            for t in self._tenants.values()
        ]


tenant_manager = TenantManager()
