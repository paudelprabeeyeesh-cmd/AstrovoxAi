"""Usage quotas enforcement per organization and user."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Quota:
    id: str
    org_id: str
    resource_type: str
    limit_value: float
    period: str
    alert_threshold: float = 0.8
    is_active: bool = True


class QuotaManager:
    def __init__(self):
        self._quotas: Dict[str, Quota] = {}
        self._usage: Dict[str, float] = {}

    def set_quota(self, org_id: str, resource_type: str, limit: float, period: str = "monthly", alert_threshold: float = 0.8) -> Quota:
        quota_id = str(uuid.uuid4())
        quota = Quota(
            id=quota_id,
            org_id=org_id,
            resource_type=resource_type,
            limit_value=limit,
            period=period,
            alert_threshold=alert_threshold,
        )
        self._quotas[quota_id] = quota
        self._usage.setdefault(f"{org_id}:{resource_type}", 0.0)
        logger.info("Set quota for org %s resource %s limit %s per %s", org_id, resource_type, limit, period)
        return quota

    def check_quota(self, org_id: str, resource_type: str, user_id: Optional[str] = None) -> dict:
        usage_key = f"{org_id}:{resource_type}"
        used = self._usage.get(usage_key, 0.0)
        quota = next((q for q in self._quotas.values() if q.org_id == org_id and q.resource_type == resource_type), None)
        limit = quota.limit_value if quota else 0.0
        allowed = limit <= 0 or used < limit
        return {
            "org_id": org_id,
            "resource_type": resource_type,
            "used": used,
            "limit": limit,
            "remaining": max(0.0, limit - used),
            "allowed": allowed,
            "alert_threshold": quota.alert_threshold if quota else 0.8,
        }

    def enforce_quota(self, org_id: str, resource_type: str, user_id: Optional[str] = None) -> None:
        result = self.check_quota(org_id, resource_type, user_id)
        if not result["allowed"]:
            logger.warning("Quota exceeded for org %s resource %s", org_id, resource_type)
            raise PermissionError(f"Quota exceeded for {resource_type}")

    def consume(self, org_id: str, resource_type: str, amount: float = 1.0) -> dict:
        usage_key = f"{org_id}:{resource_type}"
        self._usage[usage_key] = self._usage.get(usage_key, 0.0) + amount
        return self.check_quota(org_id, resource_type)

    def list_quotas(self, org_id: str) -> List[dict]:
        return [
            {
                "id": q.id,
                "org_id": q.org_id,
                "resource_type": q.resource_type,
                "limit_value": q.limit_value,
                "period": q.period,
                "alert_threshold": q.alert_threshold,
                "is_active": q.is_active,
            }
            for q in self._quotas.values()
            if q.org_id == org_id
        ]


quota_manager = QuotaManager()
