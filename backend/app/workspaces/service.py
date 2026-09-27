"""Workspace service with team management and permissions."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class WorkspaceService:
    def __init__(self) -> None:
        self._workspaces: dict[str, dict] = {}
        self._members: dict[str, list[dict]] = {}
        self._invitations: dict[str, dict] = {}

    def create_workspace(self, name: str, owner_id: str, description: Optional[str] = None) -> dict:
        workspace_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        workspace = {
            "id": workspace_id,
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }
        self._workspaces[workspace_id] = workspace
        self._members.setdefault(workspace_id, []).append({
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "user_id": owner_id,
            "role": "owner",
            "joined_at": now,
        })
        logger.info("Created workspace %s for user %s", workspace_id, owner_id)
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[dict]:
        return self._workspaces.get(workspace_id)

    def list_user_workspaces(self, user_id: str) -> list[dict]:
        return [w for w in self._workspaces.values() if w["owner_id"] == user_id or self._is_member(user_id, w["id"])]

    def _is_member(self, user_id: str, workspace_id: str) -> bool:
        return any(m["user_id"] == user_id for m in self._members.get(workspace_id, []))

    def update_workspace(self, workspace_id: str, **updates) -> Optional[dict]:
        workspace = self._workspaces.get(workspace_id)
        if not workspace:
            return None
        workspace.update({k: v for k, v in updates.items() if v is not None})
        workspace["updated_at"] = datetime.now(timezone.utc).isoformat()
        return workspace

    def delete_workspace(self, workspace_id: str, user_id: str) -> bool:
        workspace = self._workspaces.get(workspace_id)
        if not workspace or workspace["owner_id"] != user_id:
            return False
        del self._workspaces[workspace_id]
        self._members.pop(workspace_id, None)
        return True

    def invite_member(self, workspace_id: str, email: str, role: str = "member", invited_by: str = "") -> Optional[dict]:
        if workspace_id not in self._workspaces:
            return None
        token = secrets.token_urlsafe(32)
        invitation = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "email": email,
            "role": role,
            "token": token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        self._invitations[token] = invitation
        logger.info("Invited %s to workspace %s", email, workspace_id)
        return invitation

    def accept_invitation(self, token: str, user_id: str) -> Optional[dict]:
        invitation = self._invitations.get(token)
        if not invitation:
            return None
        workspace_id = invitation["workspace_id"]
        now = datetime.now(timezone.utc).isoformat()
        member = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": invitation["role"],
            "joined_at": now,
        }
        self._members.setdefault(workspace_id, []).append(member)
        del self._invitations[token]
        return member

    def get_members(self, workspace_id: str) -> list[dict]:
        return self._members.get(workspace_id, [])

    def update_member_role(self, workspace_id: str, member_id: str, role: str) -> Optional[dict]:
        for member in self._members.get(workspace_id, []):
            if member["id"] == member_id:
                member["role"] = role
                return member
        return None

    def remove_member(self, workspace_id: str, member_id: str) -> bool:
        members = self._members.get(workspace_id, [])
        for i, member in enumerate(members):
            if member["id"] == member_id:
                members.pop(i)
                return True
        return False

    def check_permission(self, user_id: str, workspace_id: str, required_role: str) -> bool:
        role_hierarchy = {"owner": 4, "admin": 3, "member": 2, "viewer": 1}
        required_level = role_hierarchy.get(required_role, 0)
        for member in self._members.get(workspace_id, []):
            if member["user_id"] == user_id:
                return role_hierarchy.get(member["role"], 0) >= required_level
        return False
