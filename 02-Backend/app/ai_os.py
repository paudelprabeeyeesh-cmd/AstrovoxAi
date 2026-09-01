"""AI Operating System — unified dashboard, workspace management, cross-project search."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Workspace:
    """An AI workspace."""
    id: str
    name: str
    owner_id: str
    description: str = ""
    created_at: float = 0.0
    settings: dict = field(default_factory=dict)
    members: list = field(default_factory=list)

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class WorkspaceManager:
    """Manage AI workspaces."""

    def __init__(self):
        self._workspaces: dict[str, Workspace] = {}

    def create(self, name: str, owner_id: str, description: str = "") -> Workspace:
        """Create a workspace."""
        import secrets
        ws = Workspace(
            id=secrets.token_hex(8),
            name=name,
            owner_id=owner_id,
            description=description,
        )
        ws.members.append(owner_id)
        self._workspaces[ws.id] = ws
        return ws

    def get(self, ws_id: str) -> Optional[Workspace]:
        return self._workspaces.get(ws_id)

    def list_for_user(self, user_id: str) -> list[Workspace]:
        return [w for w in self._workspaces.values() if user_id in w.members]

    def add_member(self, ws_id: str, user_id: str):
        ws = self._workspaces.get(ws_id)
        if ws and user_id not in ws.members:
            ws.members.append(user_id)


class PromptLibrary:
    """Universal prompt library."""

    def __init__(self):
        self._prompts: dict = {}

    def add_prompt(self, name: str, content: str, category: str = "general", tags: list = None):
        """Add a prompt to the library."""
        import secrets
        self._prompts[name] = {
            "id": secrets.token_hex(4),
            "name": name,
            "content": content,
            "category": category,
            "tags": tags or [],
            "created_at": time.time(),
            "usage_count": 0,
        }

    def get_prompt(self, name: str) -> Optional[dict]:
        prompt = self._prompts.get(name)
        if prompt:
            prompt["usage_count"] += 1
        return prompt

    def search(self, query: str) -> list[dict]:
        query_lower = query.lower()
        return [
            p for p in self._prompts.values()
            if query_lower in p["name"].lower() or query_lower in p["category"].lower()
        ]


workspace_manager = WorkspaceManager()
prompt_library = PromptLibrary()
