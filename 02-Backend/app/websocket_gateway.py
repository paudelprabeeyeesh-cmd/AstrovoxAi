"""WebSocket gateway for real-time communication."""

from typing import Dict, Optional, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")

    def disconnect(self, client_id: str) -> None:
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        for user_id, connections in self.user_connections.items():
            connections.discard(client_id)
        logger.info(f"Client disconnected: {client_id}")

    async def send_message(self, client_id: str, message: Dict[str, Any]) -> None:
        websocket = self.active_connections.get(client_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None) -> None:
        exclude = exclude or set()
        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {client_id}: {e}")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        connections = self.user_connections.get(user_id, set())
        for client_id in connections:
            await self.send_message(client_id, message)


manager = ConnectionManager()
