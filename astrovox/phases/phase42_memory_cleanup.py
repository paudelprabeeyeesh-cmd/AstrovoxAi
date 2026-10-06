"""Memory cleanup: TTL, eviction, and garbage collection."""

from __future__ import annotations

import time
from astrovox.phases._shared.compression import compress_text
from astrovox.phases.phase42_memory_storage import MemoryStore
from astrovox.phases.phase42_memory_retrieval import search


def cleanup_expired(store: MemoryStore, now: float | None = None) -> int:
    """Remove expired entries."""
    now = now or time.time()
    keys = list(store.list_keys())
    removed = 0
    for key in keys:
        row = store.get(key)
        if isinstance(row, dict) and row.get("expires", 0) and now > row["expires"]:
            store.delete(key)
            removed += 1
    return removed


def evict_low_importance(store: MemoryStore, keep: int = 100) -> int:
    """Evict lowest-importance entries down to keep count."""
    rows = {}
    for key in store.list_keys():
        r = store.get(key)
        if isinstance(r, dict):
            rows[key] = r
    scored = sorted(rows.items(), key=lambda kv: kv[1].get("importance", 0))
    removed = 0
    for key, _ in scored[:-keep]:
        store.delete(key)
        removed += 1
    return removed


def garbage_collect(store: MemoryStore) -> dict:
    """Run full cleanup: expired removal + low-importance eviction."""
    now = time.time()
    expired = cleanup_expired(store, now)
    evicted = evict_low_importance(store)
    return {"expired_removed": expired, "evicted": evicted,
            "remaining": store.count()}


class CleanupScheduler:
    """Periodic memory cleanup scheduler."""

    def __init__(self, store: MemoryStore, interval_seconds: float = 3600.0):
        self.store = store
        self.interval = interval_seconds
        self.last_run = 0.0
        self._running = False

    def should_run(self, now: float | None = None) -> bool:
        now = now or time.time()
        if not self._running:
            return True
        return now - self.last_run >= self.interval

    def run(self, now: float | None = None) -> dict:
        now = now or time.time()
        if not self.should_run(now):
            return {"skipped": True, "reason": "interval not reached"}
        result = garbage_collect(self.store)
        result["timestamp"] = now
        self.last_run = now
        return result
