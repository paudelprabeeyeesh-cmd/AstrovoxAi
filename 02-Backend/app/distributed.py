"""Distributed Systems — message queues, event-driven architecture, service discovery."""

import json
import time
import logging
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """An event in the system."""
    id: str
    event_type: str
    payload: dict
    timestamp: float
    source: str = ""


@dataclass
class Message:
    """A message in a queue."""
    id: str
    queue: str
    payload: dict
    timestamp: float
    attempts: int = 0
    max_attempts: int = 3


class EventBus:
    """In-memory event bus for event-driven architecture."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type."""
        self._subscribers[event_type] = [
            h for h in self._subscribers[event_type] if h != handler
        ]

    async def publish(self, event: Event):
        """Publish an event."""
        self._history.append(event)

        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def get_history(self, event_type: str = None, limit: int = 100) -> list[Event]:
        """Get event history."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]


class MessageQueue:
    """In-memory message queue with retry support."""

    def __init__(self):
        self._queues: dict[str, list[Message]] = defaultdict(list)
        self._processing: dict[str, Message] = {}
        self._dead_letter: list[Message] = []

    async def enqueue(self, queue: str, payload: dict) -> str:
        """Add a message to a queue."""
        import secrets
        message = Message(
            id=secrets.token_hex(8),
            queue=queue,
            payload=payload,
            timestamp=time.time(),
        )
        self._queues[queue].append(message)
        return message.id

    async def dequeue(self, queue: str) -> Optional[Message]:
        """Get the next message from a queue."""
        if self._queues[queue]:
            message = self._queues[queue].pop(0)
            self._processing[message.id] = message
            return message
        return None

    async def ack(self, message_id: str):
        """Acknowledge a message as processed."""
        self._processing.pop(message_id, None)

    async def nack(self, message_id: str, requeue: bool = True):
        """Negative acknowledge - requeue or send to dead letter."""
        message = self._processing.pop(message_id, None)
        if message:
            message.attempts += 1
            if requeue and message.attempts < message.max_attempts:
                self._queues[message.queue].append(message)
            else:
                self._dead_letter.append(message)

    def get_queue_size(self, queue: str) -> int:
        """Get queue size."""
        return len(self._queues.get(queue, []))

    def get_dead_letter(self) -> list[Message]:
        """Get dead letter messages."""
        return list(self._dead_letter)


class ServiceRegistry:
    """Service discovery registry."""

    def __init__(self):
        self._services: dict[str, dict] = {}

    def register(self, name: str, host: str, port: int, metadata: dict = None):
        """Register a service."""
        self._services[name] = {
            "host": host,
            "port": port,
            "metadata": metadata or {},
            "registered_at": time.time(),
            "last_heartbeat": time.time(),
            "status": "healthy",
        }

    def deregister(self, name: str):
        """Deregister a service."""
        self._services.pop(name, None)

    def discover(self, name: str) -> Optional[dict]:
        """Discover a service."""
        return self._services.get(name)

    def heartbeat(self, name: str):
        """Update service heartbeat."""
        if name in self._services:
            self._services[name]["last_heartbeat"] = time.time()
            self._services[name]["status"] = "healthy"

    def get_healthy_services(self) -> dict:
        """Get all healthy services."""
        now = time.time()
        healthy = {}
        for name, service in self._services.items():
            if now - service["last_heartbeat"] < 30:
                healthy[name] = service
            else:
                service["status"] = "unhealthy"
        return healthy


class IdempotencyKeyStore:
    """Store for idempotency keys to prevent duplicate processing."""

    def __init__(self, ttl: int = 3600):
        self._keys: dict[str, float] = {}
        self._ttl = ttl

    def check_and_set(self, key: str) -> bool:
        """Check if key exists and set if not. Returns True if new key."""
        self._cleanup()
        if key in self._keys:
            return False
        self._keys[key] = time.time()
        return True

    def _cleanup(self):
        """Remove expired keys."""
        cutoff = time.time() - self._ttl
        expired = [k for k, v in self._keys.items() if v < cutoff]
        for k in expired:
            del self._keys[k]


event_bus = EventBus()
message_queue = MessageQueue()
service_registry = ServiceRegistry()
idempotency_store = IdempotencyKeyStore()
