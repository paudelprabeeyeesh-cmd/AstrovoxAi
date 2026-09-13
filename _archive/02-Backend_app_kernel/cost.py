"""Resource & cost manager.

Tracks token usage, embedding cost, queue depth, and per-workspace quotas.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Quota:
    requests: int = 1000
    tokens: int = 4_000_000
    cost: float = 50.0
    storage_bytes: int = 50_000_000_000


@dataclass
class UsageRecord:
    workspace_id: str
    timestamp: float = field(default_factory=time.time)
    tokens: int = 0
    cost: float = 0.0
    requests: int = 0
    embedding_cost: float = 0.0
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostManager:
    """Per-workspace quota + cost tracking."""

    DEFAULT_PRICING = {
        "input_per_1k": 0.003,
        "output_per_1k": 0.015,
        "embedding_per_1k": 0.0001,
    }

    def __init__(self) -> None:
        self._quotas: Dict[str, Quota] = {}
        self._usage: Dict[str, List[UsageRecord]] = defaultdict(list)
        self._lock_proxy: List[Any] = []

    def set_quota(self, workspace_id: str, quota: Quota) -> None:
        self._quotas[workspace_id] = quota

    def quota(self, workspace_id: str) -> Quota:
        return self._quotas.get(workspace_id, Quota())

    def record(
        self,
        workspace_id: str,
        *,
        tokens: int = 0,
        cost: float = 0.0,
        requests: int = 1,
        embedding_cost: float = 0.0,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        rec = UsageRecord(
            workspace_id=workspace_id,
            tokens=tokens,
            cost=cost,
            requests=requests,
            embedding_cost=embedding_cost,
            model=model,
            metadata=metadata or {},
        )
        self._usage[workspace_id].append(rec)
        return rec

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        embedding_tokens: int = 0,
        model: Optional[str] = None,
    ) -> float:
        # Per-model pricing override
        if model and model in self._model_pricing:
            p = self._model_pricing[model]
        else:
            p = self.DEFAULT_PRICING
        return (
            p["input_per_1k"] * input_tokens / 1000
            + p["output_per_1k"] * output_tokens / 1000
            + p["embedding_per_1k"] * embedding_tokens / 1000
        )

    @property
    def _model_pricing(self) -> Dict[str, Dict[str, float]]:
        # Lazy override map.
        return {
            "gpt-4o": {"input_per_1k": 0.005, "output_per_1k": 0.015, "embedding_per_1k": 0.0001},
            "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006, "embedding_per_1k": 0.00002},
            "claude-3.5-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015, "embedding_per_1k": 0.0001},
        }

    def total(self, workspace_id: str) -> Dict[str, Any]:
        records = self._usage.get(workspace_id, [])
        return {
            "workspace_id": workspace_id,
            "tokens": sum(r.tokens for r in records),
            "cost": round(sum(r.cost for r in records), 6),
            "requests": sum(r.requests for r in records),
            "embedding_cost": round(sum(r.embedding_cost for r in records), 6),
            "records": len(records),
        }

    def check_quota(self, workspace_id: str) -> Dict[str, Any]:
        total = self.total(workspace_id)
        quota = self.quota(workspace_id)
        return {
            "workspace_id": workspace_id,
            "tokens_used": total["tokens"],
            "tokens_limit": quota.tokens,
            "tokens_pct": (total["tokens"] / quota.tokens) if quota.tokens else 0,
            "cost_used": total["cost"],
            "cost_limit": quota.cost,
            "cost_pct": (total["cost"] / quota.cost) if quota.cost else 0,
            "requests_used": total["requests"],
            "requests_limit": quota.requests,
            "requests_pct": (total["requests"] / quota.requests) if quota.requests else 0,
        }

    def within_quota(
        self, workspace_id: str, *, tokens: int = 0, cost: float = 0.0
    ) -> bool:
        total = self.total(workspace_id)
        quota = self.quota(workspace_id)
        return (
            total["tokens"] + tokens <= quota.tokens
            and total["cost"] + cost <= quota.cost
        )

    def summary(self) -> Dict[str, Any]:
        workspaces = list(self._usage.keys())
        return {
            "workspaces": len(workspaces),
            "totals": {
                "tokens": sum(self.total(w)["tokens"] for w in workspaces),
                "cost": round(sum(self.total(w)["cost"] for w in workspaces), 6),
                "requests": sum(self.total(w)["requests"] for w in workspaces),
            },
            "per_workspace": {w: self.total(w) for w in workspaces},
        }


_GLOBAL_COST: Optional[CostManager] = None


def get_cost_manager() -> CostManager:
    global _GLOBAL_COST
    if _GLOBAL_COST is None:
        _GLOBAL_COST = CostManager()
    return _GLOBAL_COST