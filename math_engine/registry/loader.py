"""Load and query the machine-readable topic registry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "topics.json"


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    if not _REGISTRY_PATH.exists():
        return {"topics": [], "count": 0}
    return json.loads(_REGISTRY_PATH.read_text())


def topic_status(registry: dict[str, Any], topic_id: str) -> str:
    for t in registry.get("topics", []):
        if t["id"] == topic_id:
            return t.get("status", "planned")
    return "planned"


def find_topic(registry: dict[str, Any], topic_id: str) -> dict[str, Any] | None:
    for t in registry.get("topics", []):
        if t["id"] == topic_id:
            return t
    return None
