"""Multi-tenant isolation, routing, and data residency."""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    plan: str = "free"
    is_active: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    data_residency: str = "default"
    encryption_key_id: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)
    updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)


RESIDENCY_REGIONS = {
    "default": {"region": "us-east-1", "storage": ["s3"], "compute": ["us-east-1"]},
    "eu": {"region": "eu-west-1", "storage": ["s3-eu"], "compute": ["eu-west-1"]},
    "apac": {"region": "ap-southeast-1", "storage": ["s3-apac"], "compute": ["ap-southeast-1"]},
    "gov": {"region": "us-gov-west-1", "storage": ["s3-gov"], "compute": ["us-gov-west-1"]},
    "cn": {"region": "cn-north-1", "storage": ["s3-cn"], "compute": ["cn-north-1"]},
}


class TenantManager:
    def __init__(self):
        self.tenants: Dict[str, TenantConfig] = {}
        self._default_tenant_id = os.getenv("DEFAULT_TENANT_ID", "default")

    def create_tenant(self, tenant_id: str, name: str, plan: str = "free", data_residency: str = "default") -> TenantConfig:
        config = TenantConfig(
            tenant_id=tenant_id,
            name=name,
            plan=plan,
            data_residency=data_residency,
        )
        self.tenants[tenant_id] = config
        logger.info("Created tenant %s (%s) in region %s", tenant_id, name, data_residency)
        return config

    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        return self.tenants.get(tenant_id)

    def get_residency_config(self, tenant_id: str) -> Dict[str, Any]:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return RESIDENCY_REGIONS["default"]
        return RESIDENCY_REGIONS.get(tenant.data_residency, RESIDENCY_REGIONS["default"])

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
        tenant.updated_at = datetime.now(timezone.utc).timestamp()
        return tenant

    def deactivate_tenant(self, tenant_id: str) -> bool:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.is_active = False
        tenant.updated_at = datetime.now(timezone.utc).timestamp()
        return True

    def enforce_isolation(self, tenant_id: str, resource_tenant_id: str) -> bool:
        if tenant_id != resource_tenant_id:
            raise PermissionError("Cross-tenant access denied")
        return True

    def get_default_tenant_id(self) -> str:
        return self._default_tenant_id


tenant_manager = TenantManager()


def tenant_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        tenant_id = request.headers.get("x-tenant-id") or tenant_manager.get_default_tenant_id()
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID required")
        tenant = tenant_manager.get_tenant(tenant_id)
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="Tenant not found or inactive")
        request.state.tenant_id = tenant_id
        request.state.tenant = tenant
        return await func(request, *args, **kwargs)
    return wrapper


def tenant_scoped(func):
    @wraps(func)
    async def wrapper(request: Request, resource_tenant_id: str, *args, **kwargs):
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context missing")
        tenant_manager.enforce_isolation(tenant_id, resource_tenant_id)
        return await func(request, resource_tenant_id, *args, **kwargs)
    return wrapper
