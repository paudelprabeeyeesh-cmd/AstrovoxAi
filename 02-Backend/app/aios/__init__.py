"""AIOS — Distributed AI Operating System primitives.

This package implements the core distributed-systems layer that turns
AstrovoxAI from a monolith into a coordinated set of services.  It
provides:

- Service mesh (registry, health, discovery, versioning)
- Distributed memory (hot/warm/cold/vector/semantic layers)
- Distributed scheduler (work stealing, leader, retry)
- AI runtime (agent isolation, quotas, delegation)
- Universal search (hybrid ranking, incremental indexing)
- Resource manager (load balancing, autoscaling, prediction)
- Consensus layer (leader election, distributed locks, membership)
- Self-healing (circuit breakers, retries, health probes)
- Observability (traces, metrics, SLOs, dependency map)
- Security (policy enforcement, audit, secret rotation)
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..logging_config import get_logger

logger = get_logger(__name__)


def make_id(prefix: str = "aios") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now() -> float:
    return time.time()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
