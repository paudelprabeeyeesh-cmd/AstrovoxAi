
import uuid
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Dict
from app.repositories.database.client import get_db
from .audit import log_action
from .organizations import enforce_tenant_isolation


class WorkspaceRole:
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


def create_workspace(name: str, org_id: str, owner_id: str) -> dict:
    workspace_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO workspaces (id, org_id, owner_id, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (workspace_id, org_id, owner_id, name, datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), workspace_id, owner_id, WorkspaceRole.OWNER, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    log_action(owner_id, "create_workspace", f"workspace:{workspace_id}", {"name": name, "org_id": org_id})
    return {"id": workspace_id, "name": name, "org_id": org_id, "owner_id": owner_id}


def invite_member(workspace_id: str, email: str, role: str = WorkspaceRole.MEMBER, invited_by: str = None) -> dict:
    token = secrets.token_urlsafe(32)
    invitation_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO invitations (id, workspace_id, email, role, token, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (invitation_id, workspace_id, email, role, token, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    if invited_by:
        log_action(invited_by, "invite_workspace_member", f"workspace:{workspace_id}", {"email": email})
    return {"id": invitation_id, "workspace_id": workspace_id, "email": email, "role": role, "token": token}


def accept_invitation(token: str, user_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invitations WHERE token = ?", (token,)).fetchone()
        if not row:
            return None
        member_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (member_id, row["workspace_id"], user_id, row["role"], datetime.now(timezone.utc).isoformat()),
        )
        conn.execute("DELETE FROM invitations WHERE token = ?", (token,))
        conn.commit()
    return {"workspace_id": row["workspace_id"], "user_id": user_id, "role": row["role"]}


def get_workspace_members(workspace_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT wm.id, wm.user_id, u.email, wm.role, wm.created_at
            FROM workspace_members wm
            LEFT JOIN users u ON u.id = wm.user_id
            WHERE wm.workspace_id = ?
            ORDER BY wm.created_at ASC
            """,
            (workspace_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_workspace_resources(workspace_id: str) -> dict:
    with get_db() as conn:
        tables = ["conversations", "messages", "templates", "workflows", "tools", "feedback", "memories", "knowledge_docs"]
        resources = {}
        for table in tables:
            try:
                if table in ("conversations", "messages", "templates", "workflows", "tools", "feedback", "memories", "knowledge_docs"):
                    rows = conn.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id IN (SELECT user_id FROM workspace_members WHERE workspace_id = ?)", (workspace_id,)).fetchall()
                    resources[table] = rows[0]["cnt"] if rows else 0
            except Exception:
                resources[table] = 0
        return {"workspace_id": workspace_id, "resources": resources}


def get_user_workspaces(user_id: str) -> List[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT w.id, w.name, w.org_id, w.owner_id, w.created_at, wm.role
            FROM workspaces w
            JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE wm.user_id = ?
            ORDER BY w.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_workspace(workspace_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        return dict(row) if row else None


def remove_member(workspace_id: str, user_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
            (workspace_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
