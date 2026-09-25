import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["speculative-decoding"])


DRAFT_MODELS = {
    "haiku-1b": {"size": "1B", "speed": "fast"},
    "draft-2b": {"size": "2B", "speed": "medium"},
    "mini-500m": {"size": "500M", "speed": "ultra-fast"},
}

TARGET_MODELS = {
    "opus": {"size": "500B", "speed": "slow"},
    "haiku": {"size": "10B", "speed": "medium"},
}


@router.post("/decoding/speculative")
async def speculative_decode(req: dict, user_id: str = Depends(require_verified_email)):
    prompt = req.get("prompt", "")
    draft_model = req.get("draft_model", "haiku-1b")
    target_model = req.get("target_model", "haiku")
    num_draft_tokens = req.get("num_draft_tokens", 5)
    temperature = req.get("temperature", 0.7)
    top_p = req.get("top_p", 0.95)
    with get_db() as conn:
        log_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO speculative_decoding_logs (id, user_id, prompt, draft_model, target_model, num_draft_tokens, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (log_id, user_id, prompt[:1000], draft_model, target_model, num_draft_tokens, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    # Simulate speculative decoding
    draft_tokens = [f"[d{i}]" for i in range(num_draft_tokens)]
    accepted = []
    rejected = []
    import random
    for token in draft_tokens:
        if random.random() < 0.8:
            accepted.append(token)
        else:
            rejected.append(token)
    speedup = round(len(accepted) / max(num_draft_tokens, 1) * 3, 2)
    return {
        "prompt": prompt[:100],
        "draft_model": draft_model,
        "target_model": target_model,
        "draft_tokens": draft_tokens,
        "accepted_tokens": accepted,
        "rejected_tokens": rejected,
        "speedup_factor": speedup,
        "log_id": log_id,
    }


@router.get("/decoding/models")
async def get_decoding_models(user_id: str = Depends(require_verified_email)):
    return {
        "draft_models": DRAFT_MODELS,
        "target_models": TARGET_MODELS,
    }


@router.post("/decoding/batch")
async def batch_decode(req: dict, user_id: str = Depends(require_verified_email)):
    prompts = req.get("prompts", [])
    batch_size = req.get("batch_size", 32)
    with get_db() as conn:
        batch_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO batch_decoding_logs (id, user_id, batch_size, num_prompts, created_at) VALUES (?, ?, ?, ?, ?)",
            (batch_id, user_id, batch_size, len(prompts), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    # Simulate continuous batching
    batches = [prompts[i:i + batch_size] for i in range(0, len(prompts), batch_size)]
    return {
        "batch_id": batch_id,
        "total_prompts": len(prompts),
        "batch_size": batch_size,
        "num_batches": len(batches),
        "batches": [{"index": i, "count": len(b), "prompts_preview": [p[:50] for p in b]} for i, b in enumerate(batches)],
    }


@router.get("/decoding/metrics")
async def get_decoding_metrics(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        ttft = conn.execute("SELECT AVG(ttft_ms) as avg FROM speculative_decoding_logs WHERE user_id = ?", (user_id,)).fetchone()
        speedup = conn.execute("SELECT AVG(speedup_factor) as avg FROM speculative_decoding_logs WHERE user_id = ?", (user_id,)).fetchone()
    return {
        "avg_ttft_ms": float(ttft["avg"]) if ttft and ttft["avg"] else 0,
        "avg_speedup_factor": float(speedup["avg"]) if speedup and speedup["avg"] else 0,
        "total_requests": len(getattr(ttft, '__len__', lambda: 0)()),
    }
