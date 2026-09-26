"""Organization and tenant management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Organization:
    org_id: str
    name: str
    domain: str
    plan: str
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationManager:
    def __init__(self) -> None:
        self._orgs: Dict[str, Organization] = {}

    def create(self, name: str, domain: str, plan: str = "free") -> Organization:
        org_id = uuid.uuid4().hex
        org = Organization(org_id=org_id, name=name, domain=domain, plan=plan)
        self._orgs[org_id] = org
        return org

    def get(self, org_id: str) -> Optional[Organization]:
        return self._orgs.get(org_id)

    def list_orgs(self) -> List[Organization]:
        return list(self._orgs.values())


organization_manager = OrganizationManager()
