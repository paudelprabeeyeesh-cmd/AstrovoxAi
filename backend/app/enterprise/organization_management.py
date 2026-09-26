"""Organization management service."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OrganizationManager:
    def __init__(self):
        self._orgs: Dict[str, Dict[str, Any]] = {}
        self._members: Dict[str, Dict[str, Any]] = {}

    def create_org(self, name: str, owner_id: str, plan: str = "free", settings: Optional[dict] = None) -> dict:
        org_id = str(uuid.uuid4())
        slug = name.lower().replace(" ", "-")
        org = {
            "id": org_id,
            "name": name,
            "slug": slug,
            "owner_id": owner_id,
            "plan": plan,
            "settings": settings or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._orgs[org_id] = org
        self._members[org_id] = {
            owner_id: {
                "user_id": owner_id,
                "role": "owner",
                "status": "active",
                "joined_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        logger.info("Created organization %s (%s)", name, org_id)
        return org

    def invite_member(self, org_id: str, email: str, role: str = "member", invited_by: str = "") -> dict:
        if org_id not in self._orgs:
            raise ValueError("Organization not found")
        member_id = str(uuid.uuid4())
        member = {
            "id": member_id,
            "org_id": org_id,
            "user_id": email,
            "role": role,
            "invited_by": invited_by,
            "status": "invited",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._members.setdefault(org_id, {})[email] = member
        logger.info("Invited %s to %s as %s", email, org_id, role)
        return member

    def update_org_settings(self, org_id: str, settings: dict) -> dict:
        org = self._orgs.get(org_id)
        if not org:
            raise ValueError("Organization not found")
        org["settings"] = settings
        return {"org_id": org_id, "settings": settings}

    def list_orgs(self, user_id: str) -> List[dict]:
        return [
            {
                "id": org["id"],
                "name": org["name"],
                "slug": org["slug"],
                "owner_id": org["owner_id"],
                "plan": org.get("plan", "free"),
                "member_count": len(self._members.get(org["id"], {})),
            }
            for org in self._orgs.values()
            if org["owner_id"] == user_id or user_id in self._members.get(org["id"], {})
        ]

    def get_org(self, org_id: str) -> Optional[dict]:
        return self._orgs.get(org_id)

    def list_members(self, org_id: str) -> List[dict]:
        return list(self._members.get(org_id, {}).values())


organization_manager = OrganizationManager()
