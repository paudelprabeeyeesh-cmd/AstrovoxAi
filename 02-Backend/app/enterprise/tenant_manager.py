from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TenantManager:
    def __init__(self):
        self.tenants: Dict[str, Dict[str, Any]] = {}

    def create_tenant(self, tenant_id: str, name: str, plan: str = "free", domain: Optional[str] = None) -> Dict[str, Any]:
        tenant = {
            "id": tenant_id,
            "name": name,
            "plan": plan,
            "domain": domain,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "settings": {},
            "limits": self._plan_limits(plan),
        }
        self.tenants[tenant_id] = tenant
        logger.info("Created tenant %s", tenant_id)
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        return self.tenants.get(tenant_id)

    def update_tenant(self, tenant_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        tenant.update(kwargs)
        logger.info("Updated tenant %s", tenant_id)
        return tenant

    def delete_tenant(self, tenant_id: str) -> bool:
        if tenant_id in self.tenants:
            del self.tenants[tenant_id]
            logger.info("Deleted tenant %s", tenant_id)
            return True
        return False

    def list_tenants(self) -> List[Dict[str, Any]]:
        return list(self.tenants.values())

    def _plan_limits(self, plan: str) -> Dict[str, Any]:
        limits = {
            "free": {"requests_per_day": 100, "storage_gb": 1, "users": 1},
            "pro": {"requests_per_day": 10000, "storage_gb": 100, "users": 10},
            "enterprise": {"requests_per_day": -1, "storage_gb": -1, "users": -1},
        }
        return limits.get(plan, limits["free"])


class RoleBasedAccess:
    def __init__(self):
        self.roles: Dict[str, List[str]] = {
            "admin": ["read", "write", "delete", "manage_users", "manage_tenants"],
            "editor": ["read", "write"],
            "viewer": ["read"],
        }
        self.user_roles: Dict[str, str] = {}

    def assign_role(self, user_id: str, role: str) -> None:
        if role not in self.roles:
            raise ValueError(f"Unknown role: {role}")
        self.user_roles[user_id] = role
        logger.info("Assigned role %s to user %s", role, user_id)

    def has_permission(self, user_id: str, permission: str) -> bool:
        role = self.user_roles.get(user_id, "viewer")
        return permission in self.roles.get(role, [])

    def get_user_role(self, user_id: str) -> str:
        return self.user_roles.get(user_id, "viewer")
