import logging
from fastapi import APIRouter, Depends

from ..auth import require_verified_email
from ..inference_engine import InferenceAdapter, ContextAssembler, AgenticLoop, KVCache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["inference-engine"])


@router.post("/inference/engine/prefill")
async def inference_prefill(req: dict, user_id: str = Depends(require_verified_email)):
    input_ids = req.get("input_ids", list(range(100)))
    kv_cache = KVCache(seq_len=len(input_ids))
    kv_cache.allocate()
    adapter = InferenceAdapter()
    result = adapter.prefill(input_ids, kv_cache)
    return {**result, "kv_cache_info": kv_cache.get_memory_usage()}


@router.post("/inference/engine/decode")
async def inference_decode(req: dict, user_id: str = Depends(require_verified_email)):
    seq_len = req.get("seq_len", 512)
    max_new_tokens = req.get("max_new_tokens", 20)
    temperature = req.get("temperature", 0.7)
    top_p = req.get("top_p", 0.95)
    kv_cache = KVCache(seq_len=seq_len)
    kv_cache.allocate()
    adapter = InferenceAdapter()
    tokens = adapter.decode(kv_cache, max_new_tokens, temperature, top_p)
    return {
        "generated_tokens": tokens,
        "num_tokens": len(tokens),
        "seq_len": seq_len,
        "temperature": temperature,
        "top_p": top_p,
    }


@router.post("/inference/engine/batch")
async def inference_batch(req: dict, user_id: str = Depends(require_verified_email)):
    requests = req.get("requests", [])
    max_batch = req.get("max_batch_size", 32)
    adapter = InferenceAdapter()
    result = adapter.simulate_continuous_batching(requests[:max_batch * 2])
    return result


@router.post("/inference/context/assemble")
async def assemble_context(req: dict, user_id: str = Depends(require_verified_email)):
    system_prompt = req.get("system_prompt", "")
    history = req.get("history", [])
    memory = req.get("memory", [])
    max_tokens = req.get("max_tokens", 128000)
    assembler = ContextAssembler(max_context_tokens=max_tokens)
    assembler.set_system_prompt(system_prompt)
    for h in history:
        assembler.add_history(h["role"], h["content"], h.get("tokens", 0))
    for m in memory:
        assembler.add_memory(m["content"], m.get("tokens", 0))
    budget = assembler.calculate_budget()
    prompt = assembler.assemble_prompt()
    return {
        "budget": budget,
        "prompt_length": len(prompt),
        "prompt_preview": prompt[:500],
    }


@router.post("/inference/agent/run")
async def agentic_loop_run(req: dict, user_id: str = Depends(require_verified_email)):
    task = req.get("task", "")
    max_iterations = req.get("max_iterations", 10)
    loop = AgenticLoop(max_iterations=max_iterations)
    result = loop.run(task)
    return {
        "task": task,
        "completed": True,
        "iterations": result["iterations"],
        "reasoning_steps": result["reasoning_chain_length"],
    }


@router.get("/inference/models/available")
async def get_available_models(user_id: str = Depends(require_verified_email)):
    return {
        "inference_adapters": ["vllm", "tensorrt-llm", "llama.cpp"],
        "supported_models": ["llama-3-8b", "llama-3-70b", "mixtral-8x7b", "gemma-2b", "gemma-7b"],
        "draft_models": ["1b", "2b", "500m"],
        "moe_config": {"num_experts": 8, "top_k": 2, "default_alpha": 0.01},
    }
