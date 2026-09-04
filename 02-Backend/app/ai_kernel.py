"""
AI Kernel for the Universal AI Systems Laboratory (Stage 41 Program 1).

Implements the core runtime primitives:
  * Task scheduler with priority and deadline awareness
  * Memory manager for kernel-level state
  * Actor system for message-passing concurrency
  * Event-driven runtime
  * Plugin loader
  * Checkpointing and state recovery
  * Hot reloading (signal-based)
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import os
import signal
import sys
import time
import traceback
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from .security_hardening import AuditLog, get_audit_log


class KernelState(str, Enum):
    BOOTING = "booting"
    READY = "ready"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass
class Task:
    id: str
    name: str
    handler: Callable[["Task"], Awaitable[Any]]
    args: Tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    deadline: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retries: int = 0
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "priority": int(self.priority),
            "state": self.state.value,
            "deadline": self.deadline,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ---------------------------------------------------------------------------
# Memory manager
# ---------------------------------------------------------------------------


class MemoryManager:
    """Kernel-level memory: namespaces, TTL, atomics."""

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._version: int = 0

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at < time.time():
            del self._store[key]
            return None
        return value

    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        self._store[key] = (value, expires_at)
        self._version += 1

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def keys(self, prefix: str = "") -> List[str]:
        return [k for k in self._store if k.startswith(prefix)]

    def snapshot(self) -> Dict[str, Any]:
        return {k: v[0] for k, v in self._store.items()}

    def restore(self, snapshot: Dict[str, Any]) -> None:
        self._store = {k: (v, None) for k, v in snapshot.items()}
        self._version += 1

    @property
    def version(self) -> int:
        return self._version


# ---------------------------------------------------------------------------
# Actor system
# ---------------------------------------------------------------------------


class Actor:
    """A lightweight message-passing actor.

    Each actor has an inbox (asyncio.Queue) and processes messages
    serially in its own task.  Use `send` to enqueue messages and
    `stop` to shut down.
    """

    def __init__(self, name: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        self.name = name
        self.handler = handler
        self.inbox: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    async def send(self, message: Any) -> None:
        await self.inbox.put(message)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped = True
        await self.inbox.put(None)
        if self._task:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stopped:
            msg = await self.inbox.get()
            if msg is None:
                break
            try:
                await self.handler(msg)
            except Exception as exc:
                logger.error("Actor %s handler error: %s", self.name, exc)


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------


class EventBus:
    """Asynchronous event bus with priority delivery."""

    def __init__(self, *, history_size: int = 1000) -> None:
        self._subscribers: Dict[str, List[Callable[..., Awaitable[None]]]] = defaultdict(list)
        self._history: List[Tuple[str, Any, float]] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()

    def subscribe(
        self, event_type: str, handler: Callable[..., Awaitable[None]]
    ) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Any = None) -> int:
        async with self._lock:
            self._history.append((event_type, payload, time.time()))
            if len(self._history) > self._history_size:
                self._history.pop(0)
            handlers = list(self._subscribers.get(event_type, []))
        delivered = 0
        for handler in handlers:
            try:
                await handler(payload)
                delivered += 1
            except Exception:
                pass
        return delivered

    def history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Tuple[str, Any, float]]:
        items = [
            h for h in self._history
            if event_type is None or h[0] == event_type
        ]
        return items[-limit:]


# ---------------------------------------------------------------------------
# Plugin loader
# ---------------------------------------------------------------------------


class PluginRecord:
    def __init__(
        self, name: str, path: str, module: Any, instance: Any
    ) -> None:
        self.name = name
        self.path = path
        self.module = module
        self.instance = instance
        self.loaded_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "loaded_at": self.loaded_at,
            "class": type(self.instance).__name__ if self.instance else None,
        }


class PluginLoader:
    """Load and hot-reload Python plugin modules from a directory."""

    def __init__(self, plugin_dir: str) -> None:
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: Dict[str, PluginRecord] = {}

    def load(self, name: str) -> PluginRecord:
        path = self.plugin_dir / f"{name}.py"
        if not path.exists():
            raise FileNotFoundError(f"plugin not found: {path}")
        spec = importlib.util.spec_from_file_location(f"plugin_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load plugin: {name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, "Plugin", None) or getattr(module, "Main", None)
        if cls is None:
            raise ImportError(f"plugin {name} has no Plugin class")
        instance = cls()
        record = PluginRecord(name, str(path), module, instance)
        self._plugins[name] = record
        return record

    def reload(self, name: str) -> PluginRecord:
        old = self._plugins.pop(name, None)
        if old is not None:
            for mod_name in list(sys.modules):
                if mod_name == f"plugin_{name}":
                    del sys.modules[mod_name]
        return self.load(name)

    def get(self, name: str) -> Optional[PluginRecord]:
        return self._plugins.get(name)

    def list(self) -> List[PluginRecord]:
        return list(self._plugins.values())


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


@dataclass
class Checkpoint:
    id: str
    state: Dict[str, Any]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "state_keys": sorted(self.state.keys()),
        }


class CheckpointStore:
    def __init__(self, max_checkpoints: int = 10) -> None:
        self._checkpoints: List[Checkpoint] = []
        self._max = max_checkpoints

    def save(self, state: Dict[str, Any]) -> Checkpoint:
        import uuid as _uuid

        cp = Checkpoint(id=f"cp_{_uuid.uuid4().hex[:8]}", state=dict(state))
        self._checkpoints.append(cp)
        if len(self._checkpoints) > self._max:
            self._checkpoints.pop(0)
        return cp

    def latest(self) -> Optional[Checkpoint]:
        return self._checkpoints[-1] if self._checkpoints else None

    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        for cp in self._checkpoints:
            if cp.id == checkpoint_id:
                return cp
        return None

    def list(self) -> List[Checkpoint]:
        return list(self._checkpoints)


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------


import logging as _logging  # noqa: E402

logger = _logging.getLogger(__name__)


class AIKernel:
    """Top-level kernel that ties together scheduler, memory, actors, events."""

    def __init__(
        self,
        *,
        plugin_dir: Optional[str] = None,
        max_concurrency: int = 32,
    ) -> None:
        self.state = KernelState.BOOTING
        self.memory = MemoryManager()
        self.bus = EventBus()
        self.plugins = PluginLoader(plugin_dir or "./kernel_plugins")
        self.checkpoints = CheckpointStore()
        self.scheduler = TaskScheduler(
            memory=self.memory, bus=self.bus, max_concurrency=max_concurrency
        )
        self.actors: Dict[str, Actor] = {}
        self._audit: AuditLog = get_audit_log()

    def boot(self) -> None:
        self.state = KernelState.READY
        self._audit.record(
            actor="kernel",
            action="boot",
            target="ai-kernel",
            metadata={"memory_version": self.memory.version},
        )

    def shutdown(self) -> None:
        self.state = KernelState.SHUTTING_DOWN
        for actor in self.actors.values():
            asyncio.create_task(actor.stop())
        self._audit.record(
            actor="kernel",
            action="shutdown",
            target="ai-kernel",
        )

    def register_actor(self, actor: Actor) -> None:
        self.actors[actor.name] = actor
        actor.start()

    async def send_to_actor(self, name: str, message: Any) -> bool:
        actor = self.actors.get(name)
        if actor is None:
            return False
        await actor.send(message)
        return True

    def checkpoint(self) -> Checkpoint:
        state = {
            "memory": self.memory.snapshot(),
            "memory_version": self.memory.version,
            "kernel_state": self.state.value,
            "actors": list(self.actors.keys()),
        }
        cp = self.checkpoints.save(state)
        self._audit.record(
            actor="kernel",
            action="checkpoint",
            target=cp.id,
        )
        return cp

    def restore(self, checkpoint_id: str) -> bool:
        cp = self.checkpoints.get(checkpoint_id)
        if cp is None:
            return False
        self.memory.restore(cp.state.get("memory", {}))
        self.state = KernelState.READY
        return True

    def status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "memory_version": self.memory.version,
            "memory_keys": len(self.memory.keys()),
            "actors": list(self.actors.keys()),
            "plugins": [p.to_dict() for p in self.plugins.list()],
            "checkpoints": len(self.checkpoints.list()),
            "scheduler": self.scheduler.stats(),
        }


# ---------------------------------------------------------------------------
# Task scheduler
# ---------------------------------------------------------------------------


class TaskScheduler:
    """Priority + deadline aware task scheduler."""

    def __init__(
        self,
        *,
        memory: MemoryManager,
        bus: EventBus,
        max_concurrency: int = 32,
    ) -> None:
        self.memory = memory
        self.bus = bus
        self._pending: List[Task] = []
        self._running: Dict[str, Task] = {}
        self._completed: List[Task] = []
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, asyncio.Task] = {}

    async def submit(self, task: Task) -> Task:
        async with self._lock:
            # Check dependencies
            for dep_id in task.dependencies:
                if dep_id not in [t.id for t in self._completed]:
                    if dep_id not in self._running:
                        # Dependency missing
                        task.state = TaskState.FAILED
                        task.error = f"dependency {dep_id} not found"
                        return task
            self._pending.append(task)
            self._pending.sort(key=lambda t: (int(t.priority), t.created_at))
        return task

    async def run_once(self) -> List[Task]:
        async with self._lock:
            if not self._pending:
                return []
            # Check deadlines
            now = time.time()
            self._pending = [t for t in self._pending if t.deadline is None or t.deadline > now]
            if not self._pending:
                return []
            task = self._pending.pop(0)
        return [await self._run_task(task)]

    async def run_until_empty(self) -> List[Task]:
        finished: List[Task] = []
        while True:
            step_finished = await self.run_once()
            if not step_finished:
                break
            finished.extend(step_finished)
        return finished

    async def _run_task(self, task: Task) -> Task:
        task.state = TaskState.RUNNING
        task.started_at = time.time()
        self._running[task.id] = task
        try:
            async with self._semaphore:
                result = await task.handler(task, *task.args, **task.kwargs)
                task.result = result
                task.state = TaskState.COMPLETED
        except Exception as exc:
            task.error = f"{type(exc).__name__}: {exc}"
            if task.retries < task.max_retries:
                task.retries += 1
                task.state = TaskState.PENDING
                async with self._lock:
                    self._pending.append(task)
            else:
                task.state = TaskState.FAILED
                await self.bus.publish("task.failed", task.to_dict())
        finally:
            task.completed_at = time.time()
            self._running.pop(task.id, None)
            if task.state == TaskState.COMPLETED:
                self._completed.append(task)
                await self.bus.publish("task.completed", task.to_dict())
        return task

    def stats(self) -> Dict[str, Any]:
        return {
            "pending": len(self._pending),
            "running": len(self._running),
            "completed": len(self._completed),
        }


# ---------------------------------------------------------------------------
# Hot reload
# ---------------------------------------------------------------------------


class HotReloader:
    """Watch a directory and reload plugins when files change."""

    def __init__(self, loader: PluginLoader, *, debounce_s: float = 0.5) -> None:
        self.loader = loader
        self.debounce_s = debounce_s
        self._last_modified: Dict[str, float] = {}
        self._running = False

    def scan(self) -> List[str]:
        """Return list of plugin names that need reloading."""
        changed: List[str] = []
        for path in self.loader.plugin_dir.glob("*.py"):
            name = path.stem
            mtime = path.stat().st_mtime
            if name in self._last_modified and mtime > self._last_modified[name]:
                changed.append(name)
            self._last_modified[name] = mtime
        return changed

    def reload_changed(self) -> List[str]:
        reloaded: List[str] = []
        for name in self.scan():
            try:
                self.loader.reload(name)
                reloaded.append(name)
            except Exception:
                pass
        return reloaded
