"""Custom AI Execution Engine & Compiler.

Builds the platform's "AI runtime" that:
- Parses a domain-specific language (DSL) for AI workflows
- Compiles it into an execution graph
- Optimizes the graph (dead-step elimination, parallelism, fusion)
- Schedules tasks across workers
- Executes with retries, checkpoints, and recovery
- Verifies and evaluates results

This is Stage 34 — the architectural core of the platform.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.utils import generate_id, now


def make_id(prefix: str = "exec") -> str:
    return f"{prefix}_{generate_id()}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()