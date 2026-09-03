"""Third-party integration connectors and OAuth/PKCE helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntegrationProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    SLACK = "slack"
    DISCORD = "discord"
    GOOGLE_DRIVE = "gdrive"
    ONEDRIVE = "onedrive"
    DROPBOX = "dropbox"
    NOTION = "notion"
    JIRA = "jira"
    TRELLO = "trello"


INTEGRATION_CATEGORIES: Dict[IntegrationProvider, str] = {
    IntegrationProvider.GITHUB: "developer",
    IntegrationProvider.GITLAB: "developer",
    IntegrationProvider.SLACK: "communication",
    IntegrationProvider.DISCORD: "communication",
    IntegrationProvider.GOOGLE_DRIVE: "storage",
    IntegrationProvider.ONEDRIVE: "storage",
    IntegrationProvider.DROPBOX: "storage",
    IntegrationProvider.NOTION: "productivity",
    IntegrationProvider.JIRA: "productivity",
    IntegrationProvider.TRELLO: "productivity",
}


@dataclass
class IntegrationDefinition:
    provider: IntegrationProvider
    display_name: str
    description: str
    auth_type: str  # 'oauth2' | 'webhook' | 'api_key' | 'pat'
    scopes: List[str]
    config_fields: List[str]
    category: str
    docs_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "display_name": self.display_name,
            "description": self.description,
            "auth_type": self.auth_type,
            "scopes": self.scopes,
            "config_fields": self.config_fields,
            "category": self.category,
            "docs_url": self.docs_url,
        }


class IntegrationRegistry:
    """Catalog of supported third-party integrations."""

    def __init__(self) -> None:
        self._definitions: Dict[IntegrationProvider, IntegrationDefinition] = {
            IntegrationProvider.GITHUB: IntegrationDefinition(
                provider=IntegrationProvider.GITHUB,
                display_name="GitHub",
                description="Access repositories, issues, and pull requests.",
                auth_type="oauth2",
                scopes=["repo", "read:user", "workflow"],
                config_fields=["default_org"],
                category="developer",
                docs_url="https://docs.github.com/apps/oauth-apps/building-oauth-apps",
            ),
            IntegrationProvider.GITLAB: IntegrationDefinition(
                provider=IntegrationProvider.GITLAB,
                display_name="GitLab",
                description="Connect to GitLab projects, merge requests, and pipelines.",
                auth_type="oauth2",
                scopes=["api", "read_user", "read_repository"],
                config_fields=["default_group"],
                category="developer",
            ),
            IntegrationProvider.SLACK: IntegrationDefinition(
                provider=IntegrationProvider.SLACK,
                display_name="Slack",
                description="Send messages, manage channels, read threads.",
                auth_type="oauth2",
                scopes=["chat:write", "channels:read", "users:read"],
                config_fields=["default_channel"],
                category="communication",
            ),
            IntegrationProvider.DISCORD: IntegrationDefinition(
                provider=IntegrationProvider.DISCORD,
                display_name="Discord",
                description="Post messages to channels and manage guilds.",
                auth_type="webhook",
                scopes=[],
                config_fields=["webhook_url"],
                category="communication",
            ),
            IntegrationProvider.GOOGLE_DRIVE: IntegrationDefinition(
                provider=IntegrationProvider.GOOGLE_DRIVE,
                display_name="Google Drive",
                description="Read and write files in Google Drive.",
                auth_type="oauth2",
                scopes=[
                    "https://www.googleapis.com/auth/drive.file",
                    "https://www.googleapis.com/auth/drive.readonly",
                ],
                config_fields=["default_folder"],
                category="storage",
            ),
            IntegrationProvider.ONEDRIVE: IntegrationDefinition(
                provider=IntegrationProvider.ONEDRIVE,
                display_name="OneDrive",
                description="Read and write files in Microsoft OneDrive.",
                auth_type="oauth2",
                scopes=["Files.ReadWrite", "User.Read"],
                config_fields=["default_folder"],
                category="storage",
            ),
            IntegrationProvider.DROPBOX: IntegrationDefinition(
                provider=IntegrationProvider.DROPBOX,
                display_name="Dropbox",
                description="Read and write files in Dropbox.",
                auth_type="oauth2",
                scopes=["files.content.read", "files.content.write"],
                config_fields=["default_folder"],
                category="storage",
            ),
            IntegrationProvider.NOTION: IntegrationDefinition(
                provider=IntegrationProvider.NOTION,
                display_name="Notion",
                description="Sync pages, databases, and blocks.",
                auth_type="oauth2",
                scopes=["read_content", "update_content", "insert_content"],
                config_fields=["default_database"],
                category="productivity",
            ),
            IntegrationProvider.JIRA: IntegrationDefinition(
                provider=IntegrationProvider.JIRA,
                display_name="Jira",
                description="Create and update Jira issues from workflows.",
                auth_type="oauth2",
                scopes=["read:jira-work", "write:jira-work"],
                config_fields=["default_project"],
                category="productivity",
            ),
            IntegrationProvider.TRELLO: IntegrationDefinition(
                provider=IntegrationProvider.TRELLO,
                display_name="Trello",
                description="Create cards, move them across boards, and add comments.",
                auth_type="oauth1",
                scopes=["read", "write"],
                config_fields=["default_board"],
                category="productivity",
            ),
        }

    def list(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values()]

    def get(self, provider: IntegrationProvider) -> Optional[IntegrationDefinition]:
        return self._definitions.get(provider)

    def by_category(self, category: str) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self._definitions.values() if d.category == category]


# ---------------------------------------------------------------------------
# Connection store
# ---------------------------------------------------------------------------


@dataclass
class IntegrationConnection:
    id: str
    provider: IntegrationProvider
    owner_id: str
    label: str
    status: str = "disconnected"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    scopes: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    last_error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "provider": self.provider.value,
            "owner_id": self.owner_id,
            "label": self.label,
            "status": self.status,
            "scopes": self.scopes,
            "config": self.config,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }
        if include_secrets:
            data["access_token"] = self.access_token
            data["refresh_token"] = self.refresh_token
        return data


class IntegrationStore:
    def __init__(self) -> None:
        self._connections: Dict[str, IntegrationConnection] = {}

    def add(self, connection: IntegrationConnection) -> IntegrationConnection:
        self._connections[connection.id] = connection
        return connection

    def get(self, connection_id: str) -> Optional[IntegrationConnection]:
        return self._connections.get(connection_id)

    def by_owner(self, owner_id: str) -> List[IntegrationConnection]:
        return [c for c in self._connections.values() if c.owner_id == owner_id]

    def by_provider(
        self, provider: IntegrationProvider, owner_id: Optional[str] = None
    ) -> List[IntegrationConnection]:
        return [
            c
            for c in self._connections.values()
            if c.provider == provider and (owner_id is None or c.owner_id == owner_id)
        ]

    def remove(self, connection_id: str) -> Optional[IntegrationConnection]:
        return self._connections.pop(connection_id, None)

    def list(self) -> List[IntegrationConnection]:
        return list(self._connections.values())


# ---------------------------------------------------------------------------
# OAuth/PKCE helpers
# ---------------------------------------------------------------------------


def build_pkce_pair() -> Tuple[str, str]:
    """Return (code_verifier, code_challenge) tuple using PKCE S256."""

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def sign_state(payload: Dict[str, Any], secret: str) -> str:
    import json
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{base64.urlsafe_b64encode(body.encode()).decode()}.{sig}"


def verify_state(value: str, secret: str) -> Optional[Dict[str, Any]]:
    import json
    try:
        body, sig = value.split(".", 1)
        decoded = base64.urlsafe_b64decode(body).decode()
        expected = hmac.new(
            secret.encode(), decoded.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        return json.loads(decoded)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Provider actions
# ---------------------------------------------------------------------------


class IntegrationClient:
    """High level client for performing actions across providers."""

    def __init__(self, store: Optional[IntegrationStore] = None) -> None:
        self.store = store or IntegrationStore()
        self.registry = IntegrationRegistry()

    # --- GitHub ---
    def github_list_repos(self, connection_id: str, owner: Optional[str] = None) -> Dict[str, Any]:
        conn = self._require(connection_id)
        return {
            "ok": True,
            "provider": conn.provider.value,
            "owner": owner or conn.config.get("default_org"),
            "repos": [],
        }

    def github_create_issue(
        self, connection_id: str, repo: str, title: str, body: str = ""
    ) -> Dict[str, Any]:
        self._require(connection_id)
        return {
            "ok": True,
            "provider": "github",
            "repo": repo,
            "title": title,
            "body": body,
            "url": f"https://github.com/{repo}/issues/local",
        }

    # --- GitLab ---
    def gitlab_list_projects(self, connection_id: str) -> Dict[str, Any]:
        self._require(connection_id)
        return {"ok": True, "projects": []}

    # --- Slack ---
    def slack_post_message(
        self, connection_id: str, channel: str, text: str
    ) -> Dict[str, Any]:
        self._require(connection_id)
        return {"ok": True, "channel": channel, "text": text, "ts": str(time.time())}

    # --- Discord ---
    def discord_post_message(
        self, connection_id: str, channel: str, text: str
    ) -> Dict[str, Any]:
        conn = self._require(connection_id)
        url = conn.config.get("webhook_url")
        if not url:
            return {"ok": False, "error": "webhook_url not configured"}
        return {"ok": True, "channel": channel, "text": text}

    # --- Storage ---
    def storage_list_files(
        self, connection_id: str, folder_id: str = "root"
    ) -> Dict[str, Any]:
        conn = self._require(connection_id)
        return {
            "ok": True,
            "provider": conn.provider.value,
            "folder_id": folder_id,
            "files": [],
        }

    def storage_upload(
        self, connection_id: str, name: str, content: bytes, folder_id: str = "root"
    ) -> Dict[str, Any]:
        conn = self._require(connection_id)
        return {
            "ok": True,
            "provider": conn.provider.value,
            "name": name,
            "size": len(content),
            "folder_id": folder_id,
            "id": f"file_{uuid.uuid4().hex[:8]}",
        }

    # --- Notion ---
    def notion_list_pages(self, connection_id: str, database_id: Optional[str] = None) -> Dict[str, Any]:
        conn = self._require(connection_id)
        return {
            "ok": True,
            "database_id": database_id or conn.config.get("default_database"),
            "pages": [],
        }

    # --- Jira ---
    def jira_create_issue(
        self,
        connection_id: str,
        project: str,
        summary: str,
        description: str = "",
    ) -> Dict[str, Any]:
        self._require(connection_id)
        return {
            "ok": True,
            "project": project,
            "summary": summary,
            "description": description,
            "id": f"JIRA-{uuid.uuid4().hex[:6].upper()}",
        }

    def jira_transition(
        self, connection_id: str, issue: str, status: str
    ) -> Dict[str, Any]:
        self._require(connection_id)
        return {"ok": True, "issue": issue, "status": status}

    # --- Trello ---
    def trello_create_card(
        self,
        connection_id: str,
        board: str,
        list_name: str,
        title: str,
        description: str = "",
    ) -> Dict[str, Any]:
        self._require(connection_id)
        return {
            "ok": True,
            "board": board,
            "list": list_name,
            "title": title,
            "id": f"card_{uuid.uuid4().hex[:8]}",
        }

    # --- helpers ---

    def _require(self, connection_id: str) -> IntegrationConnection:
        conn = self.store.get(connection_id)
        if conn is None:
            raise ValueError(f"Integration connection '{connection_id}' not found")
        return conn


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------


_INTEGRATION_REGISTRY: Optional[IntegrationRegistry] = None
_INTEGRATION_STORE: Optional[IntegrationStore] = None
_INTEGRATION_CLIENT: Optional[IntegrationClient] = None


def get_integration_registry() -> IntegrationRegistry:
    global _INTEGRATION_REGISTRY
    if _INTEGRATION_REGISTRY is None:
        _INTEGRATION_REGISTRY = IntegrationRegistry()
    return _INTEGRATION_REGISTRY


def get_integration_store() -> IntegrationStore:
    global _INTEGRATION_STORE
    if _INTEGRATION_STORE is None:
        _INTEGRATION_STORE = IntegrationStore()
    return _INTEGRATION_STORE


def get_integration_client() -> IntegrationClient:
    global _INTEGRATION_CLIENT
    if _INTEGRATION_CLIENT is None:
        _INTEGRATION_CLIENT = IntegrationClient(get_integration_store())
    return _INTEGRATION_CLIENT