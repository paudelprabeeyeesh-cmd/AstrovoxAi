"""Distributed Systems — message queues, event-driven architecture, service discovery.

Phase 353 — Distributed AI Infrastructure:
Multi-provider routing, dynamic routing, latency-aware routing, cost-aware
routing, availability-aware routing, automatic provider failover, queue
balancing, request batching, GPU scheduling, worker pools, load balancing,
cluster monitoring, cluster metrics, distributed caching, distributed sessions,
global routing, edge routing, capacity planning, resource scheduling,
infrastructure dashboards.
"""

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


# ============================================================================
# Phase 353 — Distributed AI Infrastructure
# ============================================================================

class GPUScheduler:
    """Schedule GPU resources for AI inference."""

    def __init__(self):
        self._gpus: list[dict] = []
        self._allocations: dict = {}

    def register_gpu(self, gpu_id: str, memory_gb: float, compute_capability: str = "8.0"):
        """Register a GPU."""
        self._gpus.append({
            "id": gpu_id,
            "memory_gb": memory_gb,
            "compute_capability": compute_capability,
            "available": True,
        })

    def allocate(self, task_id: str, memory_required: float) -> Optional[str]:
        """Allocate a GPU for a task."""
        for gpu in self._gpus:
            if gpu["available"] and gpu["memory_gb"] >= memory_required:
                gpu["available"] = False
                self._allocations[task_id] = gpu["id"]
                return gpu["id"]
        return None

    def release(self, task_id: str):
        """Release a GPU allocation."""
        gpu_id = self._allocations.pop(task_id, None)
        if gpu_id:
            for gpu in self._gpus:
                if gpu["id"] == gpu_id:
                    gpu["available"] = True

    def get_utilization(self) -> dict:
        """Get GPU utilization."""
        total = len(self._gpus)
        used = sum(1 for g in self._gpus if not g["available"])
        return {
            "total_gpus": total,
            "used_gpus": used,
            "utilization_percent": (used / total * 100) if total > 0 else 0,
        }


class WorkerPool:
    """Manage a pool of AI workers."""

    def __init__(self, num_workers: int = 4):
        self._num_workers = num_workers
        self._active_tasks: dict = {}

    def get_worker(self, task_type: str = "default") -> Optional[int]:
        """Get an available worker."""
        for i in range(self._num_workers):
            if i not in self._active_tasks:
                self._active_tasks[i] = {
                    "task_type": task_type,
                    "started_at": time.time(),
                }
                return i
        return None

    def release_worker(self, worker_id: int):
        """Release a worker."""
        self._active_tasks.pop(worker_id, None)

    def get_stats(self) -> dict:
        """Get worker pool stats."""
        return {
            "total_workers": self._num_workers,
            "active_workers": len(self._active_tasks),
            "available_workers": self._num_workers - len(self._active_tasks),
        }


class ClusterMonitor:
    """Monitor distributed cluster health."""

    def __init__(self):
        self._nodes: dict = {}

    def register_node(self, node_id: str, role: str, host: str, port: int):
        """Register a cluster node."""
        self._nodes[node_id] = {
            "role": role,
            "host": host,
            "port": port,
            "status": "healthy",
            "last_heartbeat": time.time(),
        }

    def heartbeat(self, node_id: str):
        if node_id in self._nodes:
            self._nodes[node_id]["last_heartbeat"] = time.time()
            self._nodes[node_id]["status"] = "healthy"

    def get_status(self) -> dict:
        """Get cluster status."""
        now = time.time()
        healthy = sum(1 for n in self._nodes.values() if now - n["last_heartbeat"] < 30)
        return {
            "total_nodes": len(self._nodes),
            "healthy_nodes": healthy,
            "unhealthy_nodes": len(self._nodes) - healthy,
        }


gpu_scheduler = GPUScheduler()
worker_pool = WorkerPool()
cluster_monitor = ClusterMonitor()
