"""Legal hold — preserve data for litigation and regulatory requirements."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LegalHold:
    hold_id: str
    tenant_id: str
    name: str
    description: str = ""
    scope: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    placed_by: str = ""
    released_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    released_at: Optional[str] = None


class LegalHoldManager:
    def __init__(self):
        self._holds: Dict[str, LegalHold] = {}

    def place_hold(self, tenant_id: str, name: str, description: str = "", scope: Optional[Dict[str, Any]] = None, placed_by: str = "") -> LegalHold:
        hold_id = str(uuid.uuid4())
        hold = LegalHold(
            hold_id=hold_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            scope=scope or {},
            placed_by=placed_by,
        )
        self._holds[hold_id] = hold
        logger.info("Placed legal hold %s for tenant %s", hold_id, tenant_id)
        return hold

    def release_hold(self, hold_id: str, released_by: str = "") -> Optional[LegalHold]:
        hold = self._holds.get(hold_id)
        if not hold:
            return None
        hold.status = "released"
        hold.released_by = released_by
        hold.released_at = datetime.now(timezone.utc).isoformat()
        logger.info("Released legal hold %s", hold_id)
        return hold

    def get_hold(self, hold_id: str) -> Optional[LegalHold]:
        return self._holds.get(hold_id)

    def list_holds(self, tenant_id: str, status: Optional[str] = None) -> List[dict]:
        results = [h for h in self._holds.values() if h.tenant_id == tenant_id]
        if status:
            results = [h for h in results if h.status == status]
        return [
            {
                "hold_id": h.hold_id,
                "name": h.name,
                "description": h.description,
                "scope": h.scope,
                "status": h.status,
                "placed_by": h.placed_by,
                "released_by": h.released_by,
                "created_at": h.created_at,
                "released_at": h.released_at,
            }
            for h in results
        ]

    def is_on_hold(self, tenant_id: str, resource_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        for hold in self._holds.values():
            if hold.tenant_id != tenant_id or hold.status != "active":
                continue
            scope = hold.scope
            if resource_id and scope.get("resource_id") == resource_id:
                return True
            if user_id and scope.get("user_id") == user_id:
                return True
            if not scope:
                return True
        return False


legal_hold_manager = LegalHoldManager()
