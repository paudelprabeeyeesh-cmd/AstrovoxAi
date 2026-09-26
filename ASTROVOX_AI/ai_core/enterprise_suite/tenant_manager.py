"""AI tenant management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AITenant:
    tenant_id: str
    name: str
    plan: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AITenantManager:
    def __init__(self) -> None:
        self._tenants: Dict[str, AITenant] = {}

    def create(self, name: str, plan: str = "free") -> AITenant:
        tenant_id = uuid.uuid4().hex
        tenant = AITenant(tenant_id=tenant_id, name=name, plan=plan)
        self._tenants[tenant_id] = tenant
        return tenant

    def get(self, tenant_id: str) -> Optional[AITenant]:
        return self._tenants.get(tenant_id)


ai_tenant_manager = AITenantManager()
