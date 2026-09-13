"""Real-time WebSocket service — presence, typing, notifications."""

import asyncio
import json
import time
import uuid
from typing import Optional
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect


@dataclass
class Connection:
    """A WebSocket connection."""
    websocket: WebSocket
    user_id: str
    organization_id: str = ""
    workspace_id: str = ""
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)


class ConnectionManager:
    """Manage WebSocket connections with presence and broadcasting."""

    def __init__(self):
        self._connections: dict[str, Connection] = {}  # conn_id -> Connection
        self._user_connections: dict[str, set[str]] = {}  # user_id -> set(conn_id)
        self._workspace_connections: dict[str, set[str]] = {}  # workspace_id -> set(conn_id)
        self._presence: dict[str, dict] = {}  # user_id -> presence info

    async def connect(self, websocket: WebSocket, user_id: str, organization_id: str = "", workspace_id: str = "") -> str:
        """Accept and register a new connection."""
        await websocket.accept()
        conn_id = str(uuid.uuid4())

        conn = Connection(
            websocket=websocket,
            user_id=user_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
        )
        self._connections[conn_id] = conn

        # Track user connections
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(conn_id)

        # Track workspace connections
        if workspace_id:
            if workspace_id not in self._workspace_connections:
                self._workspace_connections[workspace_id] = set()
            self._workspace_connections[workspace_id].add(conn_id)

        # Update presence
        self._presence[user_id] = {
            "status": "online",
            "last_seen": time.time(),
            "workspace_id": workspace_id,
        }

        return conn_id

    def disconnect(self, conn_id: str):
        """Remove a connection."""
        conn = self._connections.pop(conn_id, None)
        if not conn:
            return

        # Remove from user connections
        if conn.user_id in self._user_connections:
            self._user_connections[conn.user_id].discard(conn_id)
            if not self._user_connections[conn.user_id]:
                del self._user_connections[conn.user_id]

        # Remove from workspace connections
        if conn.workspace_id and conn.workspace_id in self._workspace_connections:
            self._workspace_connections[conn.workspace_id].discard(conn_id)
            if not self._workspace_connections[conn.workspace_id]:
                del self._workspace_connections[conn.workspace_id]

        # Update presence
        if conn.user_id in self._presence:
            self._presence[conn.user_id]["status"] = "offline"
            self._presence[conn.user_id]["last_seen"] = time.time()

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all of a user's connections."""
        conn_ids = self._user_connections.get(user_id, set())
        for conn_id in list(conn_ids):
            conn = self._connections.get(conn_id)
            if conn:
                try:
                    await conn.websocket.send_json(message)
                except Exception:
                    self.disconnect(conn_id)

    async def broadcast_to_workspace(self, workspace_id: str, message: dict, exclude_user: str = ""):
        """Broadcast a message to all connections in a workspace."""
        conn_ids = self._workspace_connections.get(workspace_id, set())
        for conn_id in list(conn_ids):
            conn = self._connections.get(conn_id)
            if conn and conn.user_id != exclude_user:
                try:
                    await conn.websocket.send_json(message)
                except Exception:
                    self.disconnect(conn_id)

    async def broadcast_to_organization(self, organization_id: str, message: dict):
        """Broadcast to all connections in an organization."""
        for conn in list(self._connections.values()):
            if conn.organization_id == organization_id:
                try:
                    await conn.websocket.send_json(message)
                except Exception:
                    pass

    def get_workspace_presence(self, workspace_id: str) -> list[dict]:
        """Get presence info for all users in a workspace."""
        conn_ids = self._workspace_connections.get(workspace_id, set())
        users = {}
        for conn_id in conn_ids:
            conn = self._connections.get(conn_id)
            if conn:
                users[conn.user_id] = self._presence.get(conn.user_id, {})
        return [{"user_id": uid, **info} for uid, info in users.items()]

    def get_online_users(self, workspace_id: str) -> list[str]:
        """Get list of online user IDs in a workspace."""
        presence = self.get_workspace_presence(workspace_id)
        return [p["user_id"] for p in presence if p.get("status") == "online"]

    @property
    def total_connections(self) -> int:
        return len(self._connections)


# Global connection manager
ws_manager = ConnectionManager()
