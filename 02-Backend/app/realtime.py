"""Real-time WebSocket chat with live streaming and typing indicators."""

import json
import time
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """A WebSocket connection."""
    websocket: WebSocket
    user_id: str
    conversation_id: int
    connected_at: float
    is_active: bool = True


@dataclass
class TypingIndicator:
    """A typing indicator."""
    user_id: str
    conversation_id: int
    is_typing: bool
    timestamp: float


@dataclass
class ChatMessage:
    """A real-time chat message."""
    id: str
    conversation_id: int
    user_id: str
    role: str
    content: str
    timestamp: float
    is_streaming: bool = False
    metadata: dict = field(default_factory=dict)


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self._connections: dict[str, WebSocketConnection] = {}
        self._user_connections: dict[str, list[str]] = defaultdict(list)
        self._conversation_connections: dict[int, list[str]] = defaultdict(list)
        self._typing_indicators: dict[str, TypingIndicator] = {}

    async def connect(self, websocket: WebSocket, user_id: str, conversation_id: int) -> str:
        """Accept and register a new connection."""
        await websocket.accept()
        conn_id = f"{user_id}_{conversation_id}_{time.time()}"

        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            conversation_id=conversation_id,
            connected_at=time.time(),
        )

        self._connections[conn_id] = connection
        self._user_connections[user_id].append(conn_id)
        self._conversation_connections[conversation_id].append(conn_id)

        return conn_id

    def disconnect(self, conn_id: str):
        """Remove a connection."""
        connection = self._connections.pop(conn_id, None)
        if connection:
            self._user_connections[connection.user_id] = [
                c for c in self._user_connections[connection.user_id] if c != conn_id
            ]
            self._conversation_connections[connection.conversation_id] = [
                c for c in self._conversation_connections[connection.conversation_id]
                if c != conn_id
            ]

    async def send_message(self, conn_id: str, message: dict):
        """Send a message to a specific connection."""
        connection = self._connections.get(conn_id)
        if connection and connection.is_active:
            try:
                await connection.websocket.send_json(message)
            except Exception:
                connection.is_active = False

    async def broadcast_to_conversation(self, conversation_id: int, message: dict, exclude: str = None):
        """Broadcast a message to all connections in a conversation."""
        conn_ids = self._conversation_connections.get(conversation_id, [])
        for conn_id in conn_ids:
            if conn_id != exclude:
                await self.send_message(conn_id, message)

    async def broadcast_typing(self, user_id: str, conversation_id: int, is_typing: bool):
        """Broadcast typing indicator."""
        indicator = TypingIndicator(
            user_id=user_id,
            conversation_id=conversation_id,
            is_typing=is_typing,
            timestamp=time.time(),
        )
        key = f"{user_id}_{conversation_id}"
        if is_typing:
            self._typing_indicators[key] = indicator
        else:
            self._typing_indicators.pop(key, None)

        await self.broadcast_to_conversation(conversation_id, {
            "type": "typing",
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": indicator.timestamp,
        })

    def get_typing_users(self, conversation_id: int) -> list[str]:
        """Get users who are currently typing."""
        return [
            v.user_id for v in self._typing_indicators.values()
            if v.conversation_id == conversation_id and v.is_typing
        ]

    def get_connection_count(self, conversation_id: int = None) -> int:
        """Get active connection count."""
        if conversation_id:
            return len([
                c for c in self._conversation_connections.get(conversation_id, [])
                if c in self._connections and self._connections[c].is_active
            ])
        return len([c for c in self._connections.values() if c.is_active])

    async def send_streaming_token(self, conn_id: str, token: str, message_id: str):
        """Send a streaming token."""
        await self.send_message(conn_id, {
            "type": "stream_token",
            "token": token,
            "message_id": message_id,
            "timestamp": time.time(),
        })

    async def send_streaming_complete(self, conn_id: str, message_id: str, full_content: str):
        """Signal streaming completion."""
        await self.send_message(conn_id, {
            "type": "stream_complete",
            "message_id": message_id,
            "content": full_content,
            "timestamp": time.time(),
        })

    async def send_error(self, conn_id: str, error: str):
        """Send an error message."""
        await self.send_message(conn_id, {
            "type": "error",
            "error": error,
            "timestamp": time.time(),
        })


class BackgroundWorker:
    """Background task worker with queue management."""

    def __init__(self, max_workers: int = 4):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._max_workers = max_workers
        self._workers: list[asyncio.Task] = []
        self._results: dict[str, dict] = {}
        self._is_running = False

    async def start(self):
        """Start background workers."""
        if self._is_running:
            return
        self._is_running = True
        for i in range(self._max_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self._workers.append(worker)

    async def stop(self):
        """Stop all workers."""
        self._is_running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    async def submit(self, task_id: str, coro, **kwargs) -> str:
        """Submit a task to the queue."""
        await self._queue.put({
            "task_id": task_id,
            "coro": coro,
            "kwargs": kwargs,
            "submitted_at": time.time(),
        })
        return task_id

    async def get_result(self, task_id: str) -> Optional[dict]:
        """Get task result."""
        return self._results.pop(task_id, None)

    async def _worker_loop(self, worker_name: str):
        """Worker loop that processes tasks."""
        while self._is_running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                task_id = task["task_id"]
                start_time = time.time()

                try:
                    result = await task["coro"](**task["kwargs"])
                    self._results[task_id] = {
                        "status": "completed",
                        "result": result,
                        "duration": time.time() - start_time,
                    }
                except Exception as e:
                    self._results[task_id] = {
                        "status": "failed",
                        "error": str(e),
                        "duration": time.time() - start_time,
                    }

                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            "queue_size": self._queue.qsize(),
            "active_workers": len(self._workers),
            "max_workers": self._max_workers,
            "is_running": self._is_running,
        }


connection_manager = ConnectionManager()
background_worker = BackgroundWorker()
