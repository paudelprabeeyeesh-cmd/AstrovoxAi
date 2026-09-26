import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    plan: str = "free"
    is_active: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    data_residency: str = "default"
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)


class TenantManager:
    def __init__(self):
        self.tenants: Dict[str, TenantConfig] = {}

    def create_tenant(self, tenant_id: str, name: str, plan: str = "free", data_residency: str = "default") -> TenantConfig:
        config = TenantConfig(
            tenant_id=tenant_id,
            name=name,
            plan=plan,
            data_residency=data_residency,
        )
        self.tenants[tenant_id] = config
        logger.info("Created tenant %s (%s)", tenant_id, name)
        return config

    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        return self.tenants.get(tenant_id)

    def list_tenants(self) -> List[Dict[str, Any]]:
        return [
            {
                "tenant_id": t.tenant_id,
                "name": t.name,
                "plan": t.plan,
                "is_active": t.is_active,
                "data_residency": t.data_residency,
                "created_at": t.created_at,
            }
            for t in self.tenants.values()
        ]

    def update_tenant(self, tenant_id: str, **kwargs) -> Optional[TenantConfig]:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        return tenant

    def deactivate_tenant(self, tenant_id: str) -> bool:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.is_active = False
        return True

    def enforce_isolation(self, tenant_id: str, resource_tenant_id: str) -> bool:
        if tenant_id != resource_tenant_id:
            raise PermissionError("Cross-tenant access denied")
        return True


tenant_manager = TenantManager()
