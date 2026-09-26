"""Collaboration Platform — team chat, shared workspaces, prompts, memories,
agents, documents, live cursors, comments, version history, presence, notifications.

Exposes:
- CollaborationService: unified facade for all collaboration features.
- TeamChatManager: team chat rooms, channels, direct messages.
- SharedPromptManager: share, fork, and version team prompts.
- SharedAgentManager: share agent configurations and sessions.
- SharedDocumentManager: shared documents with version history.
- CommentManager: resource-level comments and threads.
- VersionHistory: track versions for prompts, agents, documents.
- LiveCollaboration: real-time cursors, selections, presence.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and shared models
# ============================================================================


class ResourceType(str, Enum):
    WORKSPACE = "workspace"
    PROJECT = "project"
    NOTE = "note"
    DOCUMENT = "document"
    PROMPT = "prompt"
    AGENT = "agent"
    CONVERSATION = "conversation"
    TASK = "task"


class ChatChannelType(str, Enum):
    TEAM = "team"
    PROJECT = "project"
    DIRECT = "direct"
    ANNOUNCEMENT = "announcement"


# ============================================================================
# Team Chat
# ============================================================================


@dataclass
class ChatMessage:
    id: str
    channel_id: str
    user_id: str
    content: str
    created_at: float
    edited_at: float = 0.0
    is_pinned: bool = False
    reactions: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ChatChannel:
    id: str
    workspace_id: str
    name: str
    channel_type: ChatChannelType
    members: list[str] = field(default_factory=list)
    created_by: str = ""
    created_at: float = 0.0
    is_private: bool = False


class TeamChatManager:
    """Manage team chat channels and messages."""

    def __init__(self):
        self._channels: dict[str, ChatChannel] = {}
        self._messages: dict[str, list[ChatMessage]] = defaultdict(list)
        self._user_channels: dict[str, list[str]] = defaultdict(list)

    def create_channel(
        self,
        workspace_id: str,
        name: str,
        created_by: str,
        channel_type: ChatChannelType = ChatChannelType.TEAM,
        members: Optional[list[str]] = None,
        is_private: bool = False,
    ) -> ChatChannel:
        channel = ChatChannel(
            id=secrets.token_hex(8),
            workspace_id=workspace_id,
            name=name,
            channel_type=channel_type,
            members=list(members) if members else [created_by],
            created_by=created_by,
            created_at=time.time(),
            is_private=is_private,
        )
        self._channels[channel.id] = channel
        for member in channel.members:
            self._user_channels[member].append(channel.id)
        return channel

    def get_channel(self, channel_id: str) -> Optional[ChatChannel]:
        return self._channels.get(channel_id)

    def list_channels(self, workspace_id: str) -> list[ChatChannel]:
        return [c for c in self._channels.values() if c.workspace_id == workspace_id]

    def add_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
    ) -> Optional[ChatMessage]:
        channel = self._channels.get(channel_id)
        if not channel:
            return None
        message = ChatMessage(
            id=secrets.token_hex(8),
            channel_id=channel_id,
            user_id=user_id,
            content=content,
            created_at=time.time(),
        )
        self._messages[channel_id].append(message)
        return message

    def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
        before: float = 0.0,
    ) -> list[ChatMessage]:
        messages = self._messages.get(channel_id, [])
        if before > 0:
            messages = [m for m in messages if m.created_at < before]
        return sorted(messages, key=lambda m: m.created_at)[-limit:]

    def add_reaction(self, message_id: str, channel_id: str, user_id: str, emoji: str) -> bool:
        messages = self._messages.get(channel_id, [])
        for message in messages:
            if message.id == message_id:
                message.reactions.setdefault(emoji, [])
                if user_id not in message.reactions[emoji]:
                    message.reactions[emoji].append(user_id)
                return True
        return False

    def pin_message(self, message_id: str, channel_id: str) -> bool:
        messages = self._messages.get(channel_id, [])
        for message in messages:
            if message.id == message_id:
                message.is_pinned = not message.is_pinned
                return True
        return False

    def get_user_channels(self, user_id: str) -> list[ChatChannel]:
        channel_ids = self._user_channels.get(user_id, [])
        return [self._channels[cid] for cid in channel_ids if cid in self._channels]


# ============================================================================
# Shared Prompts
# ============================================================================


@dataclass
class SharedPrompt:
    id: str
    workspace_id: str
    name: str
    content: str
    description: str
    owner_id: str
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    is_public: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: dict = field(default_factory=dict)


class SharedPromptManager:
    """Manage shared prompts within a workspace."""

    def __init__(self):
        self._prompts: dict[str, SharedPrompt] = {}
        self._versions: dict[str, list[dict]] = defaultdict(list)

    def create(
        self,
        workspace_id: str,
        name: str,
        content: str,
        owner_id: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        is_public: bool = False,
    ) -> SharedPrompt:
        prompt = SharedPrompt(
            id=secrets.token_hex(8),
            workspace_id=workspace_id,
            name=name,
            content=content,
            description=description,
            owner_id=owner_id,
            tags=list(tags) if tags else [],
            is_public=is_public,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._prompts[prompt.id] = prompt
        self._record_version(prompt, "Initial version")
        return prompt

    def update(
        self,
        prompt_id: str,
        user_id: str,
        content: str,
        change_description: str = "",
    ) -> Optional[SharedPrompt]:
        prompt = self._prompts.get(prompt_id)
        if not prompt:
            return None
        prompt.content = content
        prompt.updated_at = time.time()
        self._record_version(prompt, change_description or "Updated")
        return prompt

    def _record_version(self, prompt: SharedPrompt, description: str) -> None:
        version_entry = {
            "version": prompt.version,
            "content": prompt.content,
            "description": description,
            "author_id": prompt.owner_id,
            "timestamp": time.time(),
        }
        self._versions[prompt.id].append(version_entry)

    def get(self, prompt_id: str) -> Optional[SharedPrompt]:
        return self._prompts.get(prompt_id)

    def list_workspace(self, workspace_id: str) -> list[SharedPrompt]:
        return [p for p in self._prompts.values() if p.workspace_id == workspace_id]

    def get_versions(self, prompt_id: str) -> list[dict]:
        return list(reversed(self._versions.get(prompt_id, [])))

    def fork(self, prompt_id: str, user_id: str, new_name: str) -> Optional[SharedPrompt]:
        original = self._prompts.get(prompt_id)
        if not original:
            return None
        return self.create(
            workspace_id=original.workspace_id,
            name=new_name,
            content=original.content,
            owner_id=user_id,
            description=f"Forked from {original.name}",
            tags=list(original.tags),
        )


# ============================================================================
# Shared Agents
# ============================================================================


@dataclass
class SharedAgent:
    id: str
    workspace_id: str
    name: str
    role: str
    system_prompt: str
    model: str
    temperature: float
    tools: list[str] = field(default_factory=list)
    owner_id: str = ""
    is_shared: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: dict = field(default_factory=dict)


class SharedAgentManager:
    """Manage shared agent configurations."""

    def __init__(self):
        self._agents: dict[str, SharedAgent] = {}
        self._sessions: dict[str, dict] = defaultdict(dict)

    def create(
        self,
        workspace_id: str,
        name: str,
        role: str,
        system_prompt: str,
        owner_id: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        tools: Optional[list[str]] = None,
    ) -> SharedAgent:
        agent = SharedAgent(
            id=secrets.token_hex(8),
            workspace_id=workspace_id,
            name=name,
            role=role,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            tools=list(tools) if tools else [],
            owner_id=owner_id,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._agents[agent.id] = agent
        return agent

    def get(self, agent_id: str) -> Optional[SharedAgent]:
        return self._agents.get(agent_id)

    def list_workspace(self, workspace_id: str) -> list[SharedAgent]:
        return [a for a in self._agents.values() if a.workspace_id == workspace_id]

    def share(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.is_shared = True
        agent.updated_at = time.time()
        return True

    def unshare(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.is_shared = False
        agent.updated_at = time.time()
        return True

    def start_session(self, agent_id: str, user_id: str, context: Optional[dict] = None) -> str:
        agent = self._agents.get(agent_id)
        if not agent:
            raise ValueError("Agent not found")
        session_id = secrets.token_hex(12)
        self._sessions[agent_id][session_id] = {
            "user_id": user_id,
            "started_at": time.time(),
            "context": context or {},
            "messages": [],
        }
        return session_id

    def append_message(self, agent_id: str, session_id: str, role: str, content: str) -> bool:
        sessions = self._sessions.get(agent_id, {})
        session = sessions.get(session_id)
        if not session:
            return False
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        return True


# ============================================================================
# Shared Documents
# ============================================================================


@dataclass
class DocumentVersion:
    id: str
    document_id: str
    content: str
    author_id: str
    created_at: float
    change_description: str = ""


@dataclass
class SharedDocument:
    id: str
    workspace_id: str
    title: str
    content: str
    owner_id: str
    format: str = "markdown"
    is_locked: bool = False
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: dict = field(default_factory=dict)


class SharedDocumentManager:
    """Manage shared documents with version history."""

    def __init__(self):
        self._documents: dict[str, SharedDocument] = {}
        self._versions: dict[str, list[DocumentVersion]] = defaultdict(list)

    def create(
        self,
        workspace_id: str,
        title: str,
        owner_id: str,
        content: str = "",
        format: str = "markdown",
    ) -> SharedDocument:
        doc = SharedDocument(
            id=secrets.token_hex(8),
            workspace_id=workspace_id,
            title=title,
            content=content,
            owner_id=owner_id,
            format=format,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._documents[doc.id] = doc
        self._record_version(doc, owner_id, "Initial version")
        return doc

    def update(
        self,
        document_id: str,
        user_id: str,
        content: str,
        change_description: str = "",
    ) -> Optional[SharedDocument]:
        doc = self._documents.get(document_id)
        if not doc:
            return None
        doc.content = content
        doc.updated_at = time.time()
        self._record_version(doc, user_id, change_description or "Updated")
        return doc

    def _record_version(self, doc: SharedDocument, author_id: str, description: str) -> None:
        version = DocumentVersion(
            id=secrets.token_hex(6),
            document_id=doc.id,
            content=doc.content,
            author_id=author_id,
            created_at=time.time(),
            change_description=description,
        )
        self._versions[doc.id].append(version)

    def get(self, document_id: str) -> Optional[SharedDocument]:
        return self._documents.get(document_id)

    def list_workspace(self, workspace_id: str) -> list[SharedDocument]:
        return [d for d in self._documents.values() if d.workspace_id == workspace_id]

    def get_versions(self, document_id: str) -> list[dict]:
        versions = self._versions.get(document_id, [])
        return [
            {
                "id": v.id,
                "content": v.content,
                "author_id": v.author_id,
                "change_description": v.change_description,
                "created_at": v.created_at,
            }
            for v in reversed(versions)
        ]

    def restore_version(self, document_id: str, version_id: str, user_id: str) -> Optional[SharedDocument]:
        doc = self._documents.get(document_id)
        if not doc:
            return None
        versions = self._versions.get(document_id, [])
        target = next((v for v in versions if v.id == version_id), None)
        if not target:
            return None
        doc.content = target.content
        doc.updated_at = time.time()
        self._record_version(doc, user_id, f"Restored version {version_id[:8]}")
        return doc


# ============================================================================
# Comments
# ============================================================================


@dataclass
class Comment:
    id: str
    resource_type: ResourceType
    resource_id: str
    author_id: str
    content: str
    created_at: float
    updated_at: float = 0.0
    parent_id: str = ""
    mentions: list[str] = field(default_factory=list)
    is_resolved: bool = False


class CommentManager:
    """Manage comments on shared resources."""

    def __init__(self):
        self._comments: dict[str, Comment] = {}
        self._resource_comments: dict[str, list[str]] = defaultdict(list)

    def _resource_key(self, resource_type: ResourceType, resource_id: str) -> str:
        return f"{resource_type.value}:{resource_id}"

    def add(
        self,
        resource_type: ResourceType,
        resource_id: str,
        author_id: str,
        content: str,
        parent_id: str = "",
    ) -> Comment:
        comment = Comment(
            id=secrets.token_hex(8),
            resource_type=resource_type,
            resource_id=resource_id,
            author_id=author_id,
            content=content,
            created_at=time.time(),
            parent_id=parent_id,
            mentions=[word[1:] for word in content.split() if word.startswith("@")],
        )
        self._comments[comment.id] = comment
        key = self._resource_key(resource_type, resource_id)
        self._resource_comments[key].append(comment.id)
        return comment

    def get_for_resource(
        self,
        resource_type: ResourceType,
        resource_id: str,
        include_resolved: bool = True,
    ) -> list[Comment]:
        key = self._resource_key(resource_type, resource_id)
        comment_ids = self._resource_comments.get(key, [])
        comments = [self._comments[cid] for cid in comment_ids if cid in self._comments]
        if not include_resolved:
            comments = [c for c in comments if not c.is_resolved]
        return sorted(comments, key=lambda c: c.created_at)

    def resolve(self, comment_id: str) -> bool:
        comment = self._comments.get(comment_id)
        if not comment:
            return False
        comment.is_resolved = True
        comment.updated_at = time.time()
        return True

    def get_thread(self, parent_id: str) -> list[Comment]:
        return [
            c for c in self._comments.values()
            if c.parent_id == parent_id
        ]


# ============================================================================
# Version History
# ============================================================================


@dataclass
class VersionRecord:
    id: str
    resource_type: ResourceType
    resource_id: str
    author_id: str
    snapshot: str
    description: str
    created_at: float
    metadata: dict = field(default_factory=dict)


class VersionHistory:
    """Track version history for collaboration resources."""

    def __init__(self):
        self._versions: dict[str, list[VersionRecord]] = defaultdict(list)

    def _key(self, resource_type: ResourceType, resource_id: str) -> str:
        return f"{resource_type.value}:{resource_id}"

    def record(
        self,
        resource_type: ResourceType,
        resource_id: str,
        author_id: str,
        snapshot: str,
        description: str = "",
    ) -> VersionRecord:
        version = VersionRecord(
            id=secrets.token_hex(8),
            resource_type=resource_type,
            resource_id=resource_id,
            author_id=author_id,
            snapshot=snapshot,
            description=description,
            created_at=time.time(),
        )
        key = self._key(resource_type, resource_id)
        self._versions[key].append(version)
        return version

    def get_history(
        self,
        resource_type: ResourceType,
        resource_id: str,
        limit: int = 50,
    ) -> list[dict]:
        key = self._key(resource_type, resource_id)
        versions = list(reversed(self._versions.get(key, [])))[:limit]
        return [
            {
                "id": v.id,
                "author_id": v.author_id,
                "description": v.description,
                "created_at": v.created_at,
            }
            for v in versions
        ]

    def get_snapshot(self, version_id: str) -> Optional[str]:
        for versions in self._versions.values():
            for v in versions:
                if v.id == version_id:
                    return v.snapshot
        return None


# ============================================================================
# Live Collaboration
# ============================================================================


class CursorMoveAction:
    __slots__ = ("user_id", "x", "y", "timestamp")

    def __init__(self, user_id: str, x: float, y: float):
        self.user_id = user_id
        self.x = x
        self.y = y
        self.timestamp = time.time()


class SelectionChangeAction:
    __slots__ = ("user_id", "start", "end", "timestamp")

    def __init__(self, user_id: str, start: int, end: int):
        self.user_id = user_id
        self.start = start
        self.end = end
        self.timestamp = time.time()


class LiveCollaboration:
    """Real-time collaboration state for a resource."""

    def __init__(self, resource_type: ResourceType, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self._cursors: dict[str, CursorMoveAction] = {}
        self._selections: dict[str, SelectionChangeAction] = {}
        self._participants: dict[str, dict] = {}
        self._event_log: list[dict] = []

    def set_cursor(self, user_id: str, x: float, y: float) -> None:
        self._cursors[user_id] = CursorMoveAction(user_id, x, y)

    def set_selection(self, user_id: str, start: int, end: int) -> None:
        self._selections[user_id] = SelectionChangeAction(user_id, start, end)

    def set_presence(self, user_id: str, status: str, color: str = "") -> None:
        self._participants[user_id] = {
            "user_id": user_id,
            "status": status,
            "color": color or self._color_for(user_id),
            "last_seen": time.time(),
        }

    def get_cursors(self) -> list[dict]:
        now = time.time()
        return [
            {"user_id": c.user_id, "x": c.x, "y": c.y}
            for c in self._cursors.values()
            if now - c.timestamp < 30
        ]

    def get_selections(self) -> list[dict]:
        now = time.time()
        return [
            {"user_id": s.user_id, "start": s.start, "end": s.end}
            for s in self._selections.values()
            if now - s.timestamp < 30
        ]

    def get_participants(self) -> list[dict]:
        now = time.time()
        return [
            p for p in self._participants.values()
            if now - p["last_seen"] < 60
        ]

    def log_event(self, event_type: str, user_id: str, payload: dict) -> None:
        self._event_log.append({
            "type": event_type,
            "user_id": user_id,
            "payload": payload,
            "timestamp": time.time(),
        })
        if len(self._event_log) > 500:
            self._event_log = self._event_log[-500:]

    @staticmethod
    def _color_for(user_id: str) -> str:
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"]
        idx = int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % len(colors)
        return colors[idx]


class LiveCollaborationRegistry:
    """Registry of live collaboration sessions."""

    def __init__(self):
        self._sessions: dict[str, LiveCollaboration] = {}

    def _key(self, resource_type: ResourceType, resource_id: str) -> str:
        return f"{resource_type.value}:{resource_id}"

    def get_or_create(self, resource_type: ResourceType, resource_id: str) -> LiveCollaboration:
        key = self._key(resource_type, resource_id)
        if key not in self._sessions:
            self._sessions[key] = LiveCollaboration(resource_type, resource_id)
        return self._sessions[key]

    def get(self, resource_type: ResourceType, resource_id: str) -> Optional[LiveCollaboration]:
        return self._sessions.get(self._key(resource_type, resource_id))

    def remove(self, resource_type: ResourceType, resource_id: str) -> None:
        key = self._key(resource_type, resource_id)
        self._sessions.pop(key, None)


# ============================================================================
# Presence and Notifications
# ============================================================================


class PresenceTracker:
    """Track user presence across workspaces."""

    def __init__(self):
        self._presence: dict[str, dict] = {}

    def set_online(self, user_id: str, workspace_id: str, status: str = "online"):
        key = f"{user_id}:{workspace_id}"
        self._presence[key] = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "status": status,
            "last_seen": time.time(),
        }

    def set_offline(self, user_id: str, workspace_id: str):
        key = f"{user_id}:{workspace_id}"
        if key in self._presence:
            self._presence[key]["status"] = "offline"

    def get_online_users(self, workspace_id: str) -> list[dict]:
        now = time.time()
        return [
            p for p in self._presence.values()
            if p["workspace_id"] == workspace_id and now - p["last_seen"] < 120
        ]


class NotificationCenter:
    """Manage team notifications."""

    def __init__(self):
        self._notifications: dict[str, list[dict]] = defaultdict(list)

    def notify(
        self,
        user_id: str,
        notification_type: str,
        message: str,
        source: str = "",
        source_id: str = "",
    ):
        notification = {
            "id": secrets.token_hex(8),
            "user_id": user_id,
            "type": notification_type,
            "message": message,
            "source": source,
            "source_id": source_id,
            "read": False,
            "timestamp": time.time(),
        }
        self._notifications[user_id].append(notification)
        return notification

    def get_unread(self, user_id: str) -> list[dict]:
        return [n for n in self._notifications.get(user_id, []) if not n["read"]]

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        for n in self._notifications.get(user_id, []):
            if n["id"] == notification_id:
                n["read"] = True
                return True
        return False


# ============================================================================
# Unified Collaboration Service
# ============================================================================


class CollaborationService:
    """Unified facade for all collaboration features."""

    def __init__(self):
        self.team_chat = TeamChatManager()
        self.prompts = SharedPromptManager()
        self.agents = SharedAgentManager()
        self.documents = SharedDocumentManager()
        self.comments = CommentManager()
        self.versions = VersionHistory()
        self.live = LiveCollaborationRegistry()
        self.presence = PresenceTracker()
        self.notifications = NotificationCenter()

    def create_team_chat(
        self,
        workspace_id: str,
        name: str,
        user_id: str,
        members: Optional[list[str]] = None,
    ) -> ChatChannel:
        return self.team_chat.create_channel(
            workspace_id=workspace_id,
            name=name,
            created_by=user_id,
            members=members,
        )

    def send_team_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
    ) -> Optional[ChatMessage]:
        return self.team_chat.add_message(channel_id, user_id, content)

    def share_prompt(
        self,
        workspace_id: str,
        name: str,
        content: str,
        user_id: str,
        description: str = "",
    ) -> SharedPrompt:
        return self.prompts.create(
            workspace_id=workspace_id,
            name=name,
            content=content,
            owner_id=user_id,
            description=description,
        )

    def share_agent(
        self,
        workspace_id: str,
        name: str,
        role: str,
        system_prompt: str,
        user_id: str,
    ) -> SharedAgent:
        return self.agents.create(
            workspace_id=workspace_id,
            name=name,
            role=role,
            system_prompt=system_prompt,
            owner_id=user_id,
        )

    def create_document(
        self,
        workspace_id: str,
        title: str,
        user_id: str,
        content: str = "",
    ) -> SharedDocument:
        return self.documents.create(
            workspace_id=workspace_id,
            title=title,
            owner_id=user_id,
            content=content,
        )

    def add_comment(
        self,
        resource_type: ResourceType,
        resource_id: str,
        user_id: str,
        content: str,
    ) -> Comment:
        return self.comments.add(
            resource_type=resource_type,
            resource_id=resource_id,
            author_id=user_id,
            content=content,
        )

    def record_version(
        self,
        resource_type: ResourceType,
        resource_id: str,
        author_id: str,
        snapshot: str,
        description: str = "",
    ) -> VersionRecord:
        return self.versions.record(
            resource_type=resource_type,
            resource_id=resource_id,
            author_id=author_id,
            snapshot=snapshot,
            description=description,
        )

    def get_live_session(
        self,
        resource_type: ResourceType,
        resource_id: str,
    ) -> LiveCollaboration:
        return self.live.get_or_create(resource_type, resource_id)


# Singleton
collaboration_service = CollaborationService()
