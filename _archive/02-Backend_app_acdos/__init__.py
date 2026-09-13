"""AI Cloud-Native Distributed Operating System (ACDOS).

Stage 37 of AstrovoxAI: distributed control plane, AI compute fabric,
storage, memory, model serving, orchestration, developer platform,
reliability, security, and research subsystems.

This package provides the in-process primitives that underpin the
distributed AI platform. Real deployments back these with Kubernetes,
etcd, NATS, and an object store.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ..logging_config import get_logger

logger = get_logger(__name__)


def make_id(prefix: str = "acdos") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now() -> float:
    return time.time()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
