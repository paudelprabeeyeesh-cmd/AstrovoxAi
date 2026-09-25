
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict
from repositories.database.client import get_db
from .audit import log_action


logger = logging.getLogger(__name__)


class OrganizationRole:
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    GUEST = "guest"


def create_organization(name: str, owner_id: str, plan: str = "free", description: str = "", website: str = "") -> dict:
    org_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO organizations (id, name, owner_id, plan, description, website, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (org_id, name, owner_id, plan, description, website, datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "INSERT INTO organization_members (id, org_id, user_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), org_id, owner_id, OrganizationRole.OWNER, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    log_action(owner_id, "create_organization", f"org:{org_id}", {"name": name})
    return {"id": org_id, "name": name, "owner_id": owner_id, "plan": plan}


def add_member(org_id: str, user_id: str, role: str = OrganizationRole.MEMBER, invited_by: str = "") -> dict:
    member_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO organization_members (id, org_id, user_id, role, invited_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (member_id, org_id, user_id, role, invited_by, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": member_id, "org_id": org_id, "user_id": user_id, "role": role}


def get_user_organizations(user_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT o.id, o.name, o.owner_id, o.plan, o.description, o.website, o.created_at, om.role
            FROM organizations o
            JOIN organization_members om ON o.id = om.org_id
            WHERE om.user_id = ?
            ORDER BY o.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_organization(org_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        return dict(row) if row else None


def get_org_members(org_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT om.id, om.user_id, u.email, om.role, om.invited_by, om.created_at
            FROM organization_members om
            LEFT JOIN users u ON u.id = om.user_id
            WHERE om.org_id = ?
            ORDER BY om.created_at ASC
            """,
            (org_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_user_org_role(user_id: str, org_id: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT role FROM organization_members WHERE org_id = ? AND user_id = ?",
            (org_id, user_id),
        ).fetchone()
        return row["role"] if row else None


def enforce_tenant_isolation(user_id: str, org_id: str) -> bool:
    role = get_user_org_role(user_id, org_id)
    if not role:
        raise PermissionError("User is not a member of this organization")
    return True


def remove_member(org_id: str, user_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM organization_members WHERE org_id = ? AND user_id = ?",
            (org_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def update_member_role(org_id: str, user_id: str, role: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE organization_members SET role = ? WHERE org_id = ? AND user_id = ?",
            (role, org_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
