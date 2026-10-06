"""Request queue for Astrovox inference."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Request:
    """A pending inference request."""
    id: str
    payload: dict
    priority: int = 5
    status: str = "pending"
    result: Any = None


class RequestQueue:
    """Request queue with priority support."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.pending: list[Request] = []
        self.processed = 0
        self.rejected = 0

    def enqueue(self, payload: dict, priority: int = 5) -> Request | None:
        if len(self.pending) >= self.max_size:
            self.rejected += 1
            return None
        req = Request(id=f"req_{len(self.pending)}", payload=payload, priority=priority)
        self.pending.append(req)
        self.pending.sort(key=lambda r: r.priority, reverse=True)
        return req

    def dequeue(self) -> Request | None:
        if not self.pending:
            return None
        req = self.pending.pop(0)
        req.status = "processing"
        self.processed += 1
        return req

    def complete(self, req_id: str, result: Any) -> bool:
        for req in self.pending:
            if req.id == req_id:
                req.status = "completed"
                req.result = result
                return True
        return False

    def size(self) -> int:
        return len(self.pending)

    def stats(self) -> dict:
        return {"pending": len(self.pending), "processed": self.processed,
                "rejected": self.rejected, "max_size": self.max_size}
