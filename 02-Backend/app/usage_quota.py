import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.repositories.database.client import get_db


class UsageQuotaExceeded(Exception):
    """Raised when a user exceeds the usage quota."""


@dataclass
class UsageQuota:
    id: str
    tenant_id: str
    user_id: str
    resource_type: str
    limit_value: float
    period: str
    is_active: bool = True
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)


class UsageQuotaManager:
    def __init__(self):
        self.quotas: Dict[str, UsageQuota] = {}

    def create_quota(self, tenant_id: str, user_id: str, resource_type: str, limit_value: float, period: str = "monthly") -> UsageQuota:
        quota_id = str(uuid.uuid4())
        quota = UsageQuota(
            id=quota_id,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            limit_value=limit_value,
            period=period,
        )
        self.quotas[f"{tenant_id}:{user_id}:{resource_type}:{period}"] = quota
        self._persist(quota)
        return quota

    def _persist(self, quota: UsageQuota) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO usage_quotas (id, tenant_id, user_id, resource_type, limit_value, period, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (quota.id, quota.tenant_id, quota.user_id, quota.resource_type, quota.limit_value, quota.period, 1 if quota.is_active else 0),
            )
            conn.commit()

    def load_quotas(self) -> None:
        with get_db() as conn:
            rows = conn.execute("SELECT id, tenant_id, user_id, resource_type, limit_value, period, is_active FROM usage_quotas").fetchall()
            for r in rows:
                quota = UsageQuota(
                    id=r["id"],
                    tenant_id=r["tenant_id"],
                    user_id=r["user_id"],
                    resource_type=r["resource_type"],
                    limit_value=r["limit_value"],
                    period=r["period"],
                    is_active=bool(r["is_active"]),
                )
                self.quotas[f"{quota.tenant_id}:{quota.user_id}:{quota.resource_type}:{quota.period}"] = quota

    def get_quota(self, tenant_id: str, user_id: str, resource_type: str, period: str = "monthly") -> Optional[UsageQuota]:
        return self.quotas.get(f"{tenant_id}:{user_id}:{resource_type}:{period}")

    def list_quotas(self, tenant_id: str = None) -> List[Dict[str, Any]]:
        quotas = list(self.quotas.values())
        if tenant_id:
            quotas = [q for q in quotas if q.tenant_id == tenant_id]
        return [
            {
                "id": q.id,
                "tenant_id": q.tenant_id,
                "user_id": q.user_id,
                "resource_type": q.resource_type,
                "limit_value": q.limit_value,
                "period": q.period,
                "is_active": q.is_active,
            }
            for q in quotas
        ]

    def get_usage(self, tenant_id: str, user_id: str, resource_type: str, period: str = "monthly") -> float:
        with get_db() as conn:
            if period == "daily":
                row = conn.execute(
                    "SELECT SUM(quantity) as total FROM billing_meters WHERE tenant_id = ? AND user_id = ? AND resource_type = ? AND date(created_at) = date('now')",
                    (tenant_id, user_id, resource_type),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT SUM(quantity) as total FROM billing_meters WHERE tenant_id = ? AND user_id = ? AND resource_type = ? AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
                    (tenant_id, user_id, resource_type),
                ).fetchone()
            return row["total"] if row and row["total"] else 0.0

    def check_quota(self, tenant_id: str, user_id: str, resource_type: str, quantity: float = 1.0, period: str = "monthly") -> Dict[str, Any]:
        quota = self.get_quota(tenant_id, user_id, resource_type, period)
        if not quota or not quota.is_active:
            return {"allowed": True, "reason": "no_quota"}

        current_usage = self.get_usage(tenant_id, user_id, resource_type, period)
        projected_usage = current_usage + quantity

        if projected_usage > quota.limit_value:
            return {
                "allowed": False,
                "reason": "quota_exceeded",
                "limit": quota.limit_value,
                "current_usage": current_usage,
                "projected_usage": projected_usage,
                "remaining": max(0, quota.limit_value - current_usage),
            }

        return {
            "allowed": True,
            "limit": quota.limit_value,
            "current_usage": current_usage,
            "remaining": quota.limit_value - projected_usage,
        }

    def enforce_quota(self, tenant_id: str, user_id: str, resource_type: str, quantity: float = 1.0, period: str = "monthly") -> None:
        result = self.check_quota(tenant_id, user_id, resource_type, quantity, period)
        if not result["allowed"]:
            raise UsageQuotaExceeded(f"Quota exceeded for {resource_type}: {result['reason']}")


usage_quota_manager = UsageQuotaManager()
