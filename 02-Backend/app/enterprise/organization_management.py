"""Organization management service."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.database.client import get_db
from app.enterprise.service import OrganizationService
from app.audit import log_action

logger = logging.getLogger(__name__)


class OrganizationManager:
    def __init__(self):
        self.service = OrganizationService()

    def create_org(self, name: str, owner_id: str, plan: str = "free", settings: Optional[dict] = None) -> dict:
        org, membership = self.service.create_organization(name=name, owner_id=owner_id, description="", website="")
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO organizations (id, name, slug, description, website, owner_id, plan, settings, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    org.id,
                    org.name,
                    org.slug,
                    org.description,
                    org.website,
                    owner_id,
                    plan,
                    json.dumps(settings or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        log_action(owner_id, "create_organization", f"org:{org.id}", {"name": name, "plan": plan})
        return {"id": org.id, "name": org.name, "slug": org.slug, "plan": plan}

    def invite_member(self, org_id: str, email: str, role: str = "member", invited_by: str = "") -> dict:
        with get_db() as conn:
            member_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO organization_members (id, org_id, user_id, role, invited_by, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (member_id, org_id, email, role, invited_by, "invited", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": member_id, "org_id": org_id, "email": email, "role": role}

    def update_org_settings(self, org_id: str, settings: dict) -> dict:
        with get_db() as conn:
            conn.execute("UPDATE organizations SET settings = ? WHERE id = ?", (json.dumps(settings), org_id))
            conn.commit()
        return {"org_id": org_id, "settings": settings}

    def list_orgs(self, user_id: str) -> list[dict]:
        orgs = self.service.get_user_organizations(user_id)
        return [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "owner_id": o.owner_id,
                "plan": getattr(o, "plan", "free"),
            }
            for o in orgs
        ]


import json

organization_manager = OrganizationManager()
