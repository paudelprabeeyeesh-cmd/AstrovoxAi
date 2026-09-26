import logging
import uuid

from fastapi import APIRouter, Depends

from ..auth import require_verified_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["paged-attention"])


KV_CACHE_PAGE_SIZE = 16
HBM_SIZE_BYTES = 80 * 1024 * 1024 * 1024


@router.post("/inference/paged-attention/allocate")
async def allocate_kv_cache(req: dict, user_id: str = Depends(require_verified_email)):
    seq_len = req.get("seq_len", 2048)
    page_size = req.get("page_size", KV_CACHE_PAGE_SIZE)
    num_pages = (seq_len + page_size - 1) // page_size
    page_table = {}
    allocated = 0
    total_pages_needed = num_pages
    used_memory = 0
    page_size_bytes = 512 * 1024
    total_memory_needed = total_pages_needed * page_size_bytes
    for i in range(num_pages):
        page_id = str(uuid.uuid4())
        page_table[i] = {
            "page_id": page_id,
            "page_num": i,
            "allocated": True,
            "memory_offset": i * page_size_bytes,
            "size_bytes": page_size_bytes,
        }
        allocated += 1
        used_memory += page_size_bytes
    return {
        "sequence_length": seq_len,
        "page_size": page_size,
        "num_pages": num_pages,
        "page_table": page_table,
        "memory_allocated_bytes": used_memory,
        "memory_allocated_mb": round(used_memory / (1024 * 1024), 2),
        "hbm_utilization_pct": round(used_memory / HBM_SIZE_BYTES * 100, 4),
    }


@router.post("/inference/batch/schedule")
async def continuous_batch_schedule(req: dict, user_id: str = Depends(require_verified_email)):
    max_batch_size = req.get("max_batch_size", 32)
    incoming_requests = req.get("requests", [])
    scheduled = min(len(incoming_requests), max_batch_size)
    batch = {
        "batch_id": str(uuid.uuid4()),
        "active_requests": incoming_requests[:scheduled],
        "queued_requests": incoming_requests[scheduled:],
        "batch_size": scheduled,
        "tokens_to_generate": sum(r.get("max_tokens", 100) for r in incoming_requests[:scheduled]),
    }
    return batch


@router.post("/inference/continuous-batching")
async def continuous_batching(req: dict, user_id: str = Depends(require_verified_email)):
    batch_size = req.get("batch_size", 32)
    max_seq_len = req.get("max_seq_len", 4096)
    num_layers = req.get("num_layers", 32)
    num_heads = req.get("num_heads", 32)
    hidden_size = req.get("hidden_size", 4096)
    kv_cache_per_token = 4 * num_heads * hidden_size // num_heads
    total_tokens = batch_size * max_seq_len
    total_cache_bytes = total_tokens * kv_cache_per_token
    pages = total_cache_bytes // (KV_CACHE_PAGE_SIZE * 512)
    return {
        "batch_size": batch_size,
        "max_seq_len": max_seq_len,
        "total_tokens": total_tokens,
        "kv_cache_bytes": total_cache_bytes,
        "pages_required": int(pages),
        "memory_per_request_bytes": total_cache_bytes // batch_size if batch_size > 0 else 0,
        "estimated_throughput_tokens_per_sec": round(batch_size * 50, 2),
        "estimated_ttft_ms": round(1000 * max_seq_len / (batch_size * 100), 2),
    }
