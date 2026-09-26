"""Usage quotas enforcement per organization and user."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.database.client import get_db
from app.usage_quota import usage_quota_manager, UsageQuotaExceeded

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
        self._quotas: dict[str, Quota] = {}

    def set_quota(self, org_id: str, resource_type: str, limit: float, period: str = "monthly", alert_threshold: float = 0.8) -> Quota:
        quota_id = str(uuid.uuid4())
        quota = Quota(id=quota_id, org_id=org_id, resource_type=resource_type, limit_value=limit, period=period, alert_threshold=alert_threshold)
        self._quotas[quota_id] = quota
        usage_quota_manager.create_quota(tenant_id=org_id, user_id="*", resource_type=resource_type, limit_value=limit, period=period)
        return quota

    def check_quota(self, org_id: str, resource_type: str, user_id: Optional[str] = None) -> dict:
        result = usage_quota_manager.check_quota(tenant_id=org_id, user_id=user_id or "*", resource_type=resource_type)
        return result

    def enforce_quota(self, org_id: str, resource_type: str, user_id: Optional[str] = None) -> None:
        usage_quota_manager.enforce_quota(tenant_id=org_id, user_id=user_id or "*", resource_type=resource_type)

    def list_quotas(self, org_id: str) -> list[dict]:
        return [
            {
                "id": q.id,
                "org_id": q.org_id,
                "resource_type": q.resource_type,
                "limit_value": q.limit_value,
                "period": q.period,
                "alert_threshold": q.alert_threshold,
            }
            for q in self._quotas.values()
            if q.org_id == org_id
        ]


quota_manager = QuotaManager()
