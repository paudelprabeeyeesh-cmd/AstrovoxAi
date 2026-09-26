"""AI RBAC."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIPermission:
    permission_id: str
    role: str
    resource: str
    action: str


class AIRBAC:
    def __init__(self) -> None:
        self._permissions: Dict[str, AIPermission] = {}

    def add_permission(self, permission: AIPermission) -> None:
        self._permissions[permission.permission_id] = permission

    def check(self, role: str, resource: str, action: str) -> bool:
        for permission in self._permissions.values():
            if permission.role == role and permission.resource == resource and permission.action == action:
                return True
        return False


ai_rbac = AIRBAC()
