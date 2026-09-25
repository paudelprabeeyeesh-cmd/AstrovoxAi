"""WebSocket gateway for real-time communication."""

from typing import Dict, Any, Optional, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import json
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WebSocketConnection:
    def __init__(self, websocket: WebSocket, client_id: str, user_id: Optional[str] = None):
        self.websocket = websocket
        self.client_id = client_id
        self.user_id = user_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_ping = datetime.now(timezone.utc)

    async def send(self, message: Dict[str, Any]) -> None:
        if self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {self.client_id}: {e}")

    async def close(self, code: int = 1000) -> None:
        try:
            await self.websocket.close(code=code)
        except Exception:
            pass


class WebSocketGateway:
    _connections: Dict[str, WebSocketConnection] = {}
    _user_connections: Dict[str, Set[str]] = {}

    @classmethod
    async def connect(cls, websocket: WebSocket, client_id: str, user_id: Optional[str] = None) -> WebSocketConnection:
        await websocket.accept()
        conn = WebSocketConnection(websocket=websocket, client_id=client_id, user_id=user_id)
        cls._connections[client_id] = conn
        if user_id:
            if user_id not in cls._user_connections:
                cls._user_connections[user_id] = set()
            cls._user_connections[user_id].add(client_id)
        return conn

    @classmethod
    def disconnect(cls, client_id: str) -> None:
        conn = cls._connections.pop(client_id, None)
        if conn and conn.user_id:
            user_conns = cls._user_connections.get(conn.user_id, set())
            user_conns.discard(client_id)

    @classmethod
    async def send_to_client(cls, client_id: str, message: Dict[str, Any]) -> None:
        conn = cls._connections.get(client_id)
        if conn:
            await conn.send(message)

    @classmethod
    async def send_to_user(cls, user_id: str, message: Dict[str, Any]) -> None:
        client_ids = cls._user_connections.get(user_id, set())
        for cid in client_ids:
            await cls.send_to_client(cid, message)

    @classmethod
    async def broadcast(cls, message: Dict[str, Any], exclude: Optional[Set[str]] = None) -> None:
        exclude = exclude or set()
        for client_id, conn in cls._connections.items():
            if client_id not in exclude:
                await conn.send(message)
