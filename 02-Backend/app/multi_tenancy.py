
import uuid
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


class TenantManager:
    def __init__(self):
        self.tenants = {}

    def create_tenant(self, tenant_id, config):
        self.tenants[tenant_id] = config

    def get_tenant(self, tenant_id):
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not found")
        return self.tenants[tenant_id]

    def list_tenants(self):
        return list(self.tenants.keys())


def generate_tenant_id(org_name: str) -> str:
    slug = ''.join(c for c in org_name.lower() if c in string.ascii_lowercase + string.digits() if c in string.ascii_lowercase + string.digits')
    slug = slug[:20] if slug else 'org'
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f"tenant-{slug}-{timestamp}"


def create_tenant(org_id: str, org_name: str, owner_id: str, config: Optional[Dict[str, Any]] = None) -> dict:
    tenant_id = generate_tenant_id(org_name)
    config = config or {}
    with get_db() as conn:
        conn.execute(
            "UPDATE organizations SET tenant_id = ?, updated_at = ? WHERE id = ?",
            (tenant_id, datetime.now(timezone.utc).isoformat(), org_id),
        )
        conn.execute(
            "INSERT INTO tenant_configs (id, tenant_id, org_id, config_key, config_value, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), tenant_id, org_id, 'tenant_config', str(config), datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    log_action(owner_id, "create_tenant", f"org:{org_id}", {"tenant_id": tenant_id})
    return {"tenant_id": tenant_id, "org_id": org_id}


def get_tenant_by_org(org_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT tenant_id FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not row or not row["tenant_id"]:
            return None
        tenant_id = row["tenant_id"]
        configs = conn.execute("SELECT config_key, config_value FROM tenant_configs WHERE tenant_id = ?", (tenant_id,)).fetchall()
        config = {r["config_key"]: r["config_value"] for r in configs}
        return {"tenant_id": tenant_id, "org_id": org_id, "config": config}


def get_tenant_by_id(tenant_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT id, name, owner_id, plan, tenant_id FROM organizations WHERE tenant_id = ?", (tenant_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def list_tenants(limit: int = 100, offset: int = 0) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, owner_id, plan, tenant_id, status, created_at FROM organizations WHERE tenant_id IS NOT NULL ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def update_tenant_config(tenant_id: str, config_key: str, config_value: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT id, org_id FROM organizations WHERE tenant_id = ?", (tenant_id,)).fetchone()
        if not row:
            raise ValueError("Tenant not found")
        org_id = row["id"]
        existing = conn.execute("SELECT id FROM tenant_configs WHERE tenant_id = ? AND config_key = ?", (tenant_id, config_key)).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            conn.execute("UPDATE tenant_configs SET config_value = ?, updated_at = ? WHERE id = ?", (config_value, now, existing["id"]))
        else:
            conn.execute(
                "INSERT INTO tenant_configs (id, tenant_id, org_id, config_key, config_value, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), tenant_id, org_id, config_key, config_value, now, now),
            )
        conn.commit()
    return {"tenant_id": tenant_id, "config_key": config_key}


def delete_tenant(tenant_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM organizations WHERE tenant_id = ?", (tenant_id,)).fetchone()
        if not row:
            return False
        org_id = row["id"]
        conn.execute("DELETE FROM tenant_configs WHERE tenant_id = ?", (tenant_id,))
        conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        conn.commit()
    log_action(requester_id, "delete_tenant", f"tenant:{tenant_id}", {"org_id": org_id})
    return True


def provision_tenant(org_id: str, plan: str = "enterprise", features: Optional[List[str]] = None) -> dict:
    features = features or []
    tenant_info = create_tenant(org_id, f"org-{org_id[:8]}", org_id, {"plan": plan, "features": features})
    quota_defaults = {
        "api_calls": {"limit": 100000 if plan == "enterprise" else 10000, "period": "monthly"},
        "storage_gb": {"limit": 500 if plan == "enterprise" else 50, "period": "monthly"},
        "users": {"limit": 100 if plan == "enterprise" else 10, "period": "monthly"},
        "ai_tokens": {"limit": 1000000 if plan == "enterprise" else 50000, "period": "monthly"},
    }
    for resource, limits in quota_defaults.items():
        create_quota(org_id, resource, limits["limit"], limits["period"])
    return {**tenant_info, "provisioned": True, "features": features}


def enforce_tenant_isolation(org_id: str, user_id: str, resource_org_id: Optional[str] = None) -> bool:
    target_org = resource_org_id or org_id
    from .organizations import get_user_org_role
    role = get_user_org_role(user_id, target_org)
    if not role:
        raise PermissionError("User is not authorized for this tenant")
    return True
