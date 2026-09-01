"""AI Collaboration Suite — shared workspaces, team chat, live collaboration."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TeamWorkspace:
    """A team workspace."""
    id: str
    name: str
    org_id: str
    members: list = field(default_factory=list)
    resources: list = field(default_factory=list)
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class CollaborationSuite:
    """AI collaboration suite."""

    def __init__(self):
        self._workspaces: dict[str, TeamWorkspace] = {}
        self._meetings: dict = {}

    def create_workspace(self, name: str, org_id: str, creator_id: str) -> TeamWorkspace:
        """Create a workspace."""
        import secrets
        ws = TeamWorkspace(
            id=secrets.token_hex(8),
            name=name,
            org_id=org_id,
            members=[creator_id],
        )
        self._workspaces[ws.id] = ws
        return ws

    def add_member(self, ws_id: str, user_id: str):
        ws = self._workspaces.get(ws_id)
        if ws and user_id not in ws.members:
            ws.members.append(user_id)

    def add_resource(self, ws_id: str, resource_type: str, resource_id: str):
        ws = self._workspaces.get(ws_id)
        if ws:
            ws.resources.append({"type": resource_type, "id": resource_id})

    def get_workspaces(self, org_id: str = None) -> list:
        workspaces = list(self._workspaces.values())
        if org_id:
            workspaces = [w for w in workspaces if w.org_id == org_id]
        return workspaces


collab_suite = CollaborationSuite()
