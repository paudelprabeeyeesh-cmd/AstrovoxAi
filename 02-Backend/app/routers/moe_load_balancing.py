import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["moe-load-balancing"])


class MoERouter:
    def __init__(self, num_experts: int = 8, top_k: int = 2):
        self.num_experts = num_experts
        self.top_k = top_k
        self.load_balance_loss = 0.0
        self.expert_usage = {i: 0 for i in range(num_experts)}

    def route_token(self, token_embedding: list) -> tuple[int, list[int]]:
        import random
        scores = [random.random() for _ in range(self.num_experts)]
        top_experts = sorted(range(self.num_experts), key=lambda e: scores[e], reverse=True)[:self.top_k]
        for e in top_experts:
            self.expert_usage[e] += 1
        return top_experts[0], top_experts

    def compute_load_balance_loss(self) -> float:
        total = sum(self.expert_usage.values())
        if total == 0:
            return 0.0
        alpha = 0.01
        loss = 0.0
        for i in range(self.num_experts):
            f_i = self.expert_usage[i] / total
            p_i = 1.0 / self.num_experts
            loss += f_i * p_i
        self.load_balance_loss = alpha * self.num_experts * loss
        return self.load_balance_loss

    def get_routing_stats(self) -> dict:
        return {
            "num_experts": self.num_experts,
            "top_k": self.top_k,
            "expert_usage": self.expert_usage,
            "load_balance_loss": round(self.load_balance_loss, 6),
            "utilization": {str(k): v for k, v in self.expert_usage.items()},
        }


_router_cache = {}


@router.post("/moe/setup")
async def setup_moe(req: dict, user_id: str = Depends(require_verified_email)):
    num_experts = req.get("num_experts", 8)
    top_k = req.get("top_k", 2)
    run_id = str(uuid.uuid4())
    _router_cache[run_id] = MoERouter(num_experts=num_experts, top_k=top_k)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO moe_runs (id, user_id, num_experts, top_k, created_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, user_id, num_experts, top_k, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"run_id": run_id, "num_experts": num_experts, "top_k": top_k}


@router.post("/moe/route")
async def route_tokens(req: dict, run_id: str, user_id: str = Depends(require_verified_email)):
    if run_id not in _router_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    router = _router_cache[run_id]
    tokens = req.get("tokens", [])
    route_results = []
    for i, token in enumerate(tokens):
        expert, top_experts = router.route_token(token.get("embedding", [0.0]))
        route_results.append({
            "token_index": i,
            "selected_expert": expert,
            "top_k_experts": top_experts,
            "token_preview": str(token.get("content", ""))[:50],
        })
    loss = router.compute_load_balance_loss()
    stats = router.get_routing_stats()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO moe_routing_logs (id, run_id, token_count, load_balance_loss, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), run_id, len(tokens), loss, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"run_id": run_id, "tokens_processed": len(tokens), "load_balance_loss": loss, "routing_stats": stats, "route_results": route_results[:20]}


@router.get("/moe/stats/{run_id}")
async def get_moe_stats(run_id: str, user_id: str = Depends(require_verified_email)):
    if run_id not in _router_cache:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"stats": _router_cache[run_id].get_routing_stats()}
