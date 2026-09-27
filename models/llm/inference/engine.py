import argparse
import asyncio
import json
import logging
import math
import os
import sys
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import get_device, load_config, set_cpu_threads

logger = logging.getLogger(__name__)

REQUEST_COUNTER = Counter(
    "inference_requests_total", "Total inference requests", ["endpoint", "status"]
)
LATENCY_HISTOGRAM = Histogram("inference_latency_seconds", "Inference latency", ["endpoint"])


class InferenceError(Exception):
    pass


class InvalidRequestError(InferenceError):
    pass


@dataclass
class SamplingParams:
    temperature: float = 1.0
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float = 1.0
    max_new_tokens: int = 100
    stop: list[str] | None = None


@dataclass
class GenerationOutput:
    text: str
    token_ids: list[int]
    num_tokens: int
    finish_reason: str
    prompt_tokens: int
    latency_ms: float


class PagedKVCache:
    def __init__(
        self,
        num_layers: int,
        num_heads: int,
        head_dim: int,
        block_size: int = 16,
        max_blocks: int = 1024,
        device: torch.device = None,
        dtype: torch.dtype = None,
    ):
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.device = device or torch.device("cpu")
        self.dtype = dtype or torch.float32
        self.key_blocks: dict[int, torch.Tensor] = {}
        self.value_blocks: dict[int, torch.Tensor] = {}
        self.free_blocks = list(range(max_blocks))
        self.allocated: list[int] = []
        self.seq_map: dict[str, list[int]] = {}
        self.seq_lengths: dict[str, int] = {}

    def _allocate_block(self) -> int:
        if not self.free_blocks:
            raise MemoryError("Paged KV cache exhausted")
        block_id = self.free_blocks.pop(0)
        self.allocated.append(block_id)
        return block_id

    def _free_sequence(self, seq_id: str):
        blocks = self.seq_map.pop(seq_id, [])
        for b in blocks:
            if b in self.allocated:
                self.allocated.remove(b)
            self.free_blocks.append(b)
            self.key_blocks.pop(b, None)
            self.value_blocks.pop(b, None)
        self.seq_lengths.pop(seq_id, None)

    def reset(self):
        self.free_blocks = list(range(self.max_blocks))
        self.key_blocks.clear()
        self.value_blocks.clear()
        self.allocated.clear()
        self.seq_map.clear()
        self.seq_lengths.clear()

    def get(self, seq_id: str) -> tuple[torch.Tensor | None, torch.Tensor | None]:
        blocks = self.seq_map.get(seq_id, [])
        if not blocks:
            return None, None
        keys = [self.key_blocks[b] for b in blocks]
        values = [self.value_blocks[b] for b in blocks]
        return torch.cat(keys, dim=2), torch.cat(values, dim=2)

    def allocate(self, seq_id: str, num_tokens: int):
        self._free_sequence(seq_id)
        num_blocks = max(1, math.ceil(num_tokens / self.block_size))
        if num_blocks > len(self.free_blocks):
            raise MemoryError(f"Need {num_blocks} blocks, only {len(self.free_blocks)} free")
        block_ids = [self._allocate_block() for _ in range(num_blocks)]
        self.seq_map[seq_id] = block_ids
        self.seq_lengths[seq_id] = num_tokens
        for b in block_ids:
            self.key_blocks[b] = torch.zeros(
                self.num_layers,
                self.num_heads,
                self.block_size,
                self.head_dim,
                device=self.device,
                dtype=self.dtype,
            )
            self.value_blocks[b] = torch.zeros(
                self.num_layers,
                self.num_heads,
                self.block_size,
                self.head_dim,
                device=self.device,
                dtype=self.dtype,
            )

    def update(self, seq_id: str, layer_idx: int, key: torch.Tensor, value: torch.Tensor):
        blocks = self.seq_map.get(seq_id, [])
        if not blocks:
            raise KeyError(f"Sequence {seq_id} not allocated")
        total = self.seq_lengths.get(seq_id, 0)
        offset = total - key.size(2)
        block_idx = offset // self.block_size
        intra_offset = offset % self.block_size
        k_block = self.key_blocks[blocks[block_idx]]
        v_block = self.value_blocks[blocks[block_idx]]
        k_block[layer_idx, :, intra_offset : intra_offset + key.size(2), :] = key
        v_block[layer_idx, :, intra_offset : intra_offset + value.size(2), :] = value
        self.seq_lengths[seq_id] = total + key.size(2)

    def get_length(self, seq_id: str) -> int:
        return self.seq_lengths.get(seq_id, 0)


def _apply_repetition_penalty(
    logits: torch.Tensor, token_ids: list[int], penalty: float
) -> torch.Tensor:
    if penalty == 1.0 or not token_ids:
        return logits
    unique = set(token_ids)
    for tid in unique:
        if logits[..., tid] < 0:
            logits[..., tid] *= penalty
        else:
            logits[..., tid] /= penalty
    return logits


def _sample(
    logits: torch.Tensor, params: SamplingParams, token_ids: list[int]
) -> tuple[torch.Tensor, torch.Tensor]:
    logits = _apply_repetition_penalty(logits, token_ids, params.repetition_penalty)
    if params.temperature != 1.0:
        logits = logits / params.temperature
    if params.top_k is not None and params.top_k > 0:
        top_k = min(params.top_k, logits.size(-1))
        top_vals, _ = torch.topk(logits, top_k)
        min_val = top_vals[..., -1, None]
        logits = torch.where(
            logits < min_val,
            torch.tensor(float("-inf"), device=logits.device, dtype=logits.dtype),
            logits,
        )
    if params.top_p is not None and 0.0 < params.top_p < 1.0:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        probs = F.softmax(sorted_logits, dim=-1)
        cumprobs = torch.cumsum(probs, dim=-1)
        mask = cumprobs > params.top_p
        mask[..., 1:] = mask[..., :-1].clone()
        mask[..., 0] = False
        sorted_logits = torch.where(
            mask,
            torch.tensor(float("-inf"), device=logits.device, dtype=logits.dtype),
            sorted_logits,
        )
        logits = torch.zeros_like(logits).scatter_(-1, sorted_idx, sorted_logits)
    probs = F.softmax(logits, dim=-1)
    next_token = torch.multinomial(probs, num_samples=1)
    return next_token, probs


class SpeculativeDecoder:
    def __init__(
        self,
        model: nn.Module,
        draft_model: nn.Module | None = None,
        draft_steps: int = 4,
        device: torch.device = None,
    ):
        self.model = model
        self.draft_model = draft_model
        self.draft_steps = draft_steps
        self.device = device or next(model.parameters()).device

    def generate(
        self, input_ids: torch.Tensor, params: SamplingParams, tokenizer
    ) -> GenerationOutput:
        accepted = 0
        generated: list[int] = []
        current = input_ids
        start = time.perf_counter()
        for _ in range(math.ceil(params.max_new_tokens / self.draft_steps)):
            draft = current
            for _ in range(self.draft_steps):
                with torch.no_grad():
                    out = (
                        self.draft_model(draft)
                        if self.draft_model is not None
                        else self.model(draft)
                    )
                logits = out["logits"][:, -1, :]
                next_t, _ = _sample(logits, params, generated)
                draft = torch.cat([draft, next_t], dim=1)
            with torch.no_grad():
                out = self.model(draft)
            model_logits = out["logits"]
            draft_logits_list = []
            if self.draft_model is not None:
                for step in range(self.draft_steps):
                    with torch.no_grad():
                        dout = self.draft_model(
                            draft[:, : draft.size(1) - self.draft_steps + step + 1]
                        )
                    draft_logits_list.append(dout["logits"][:, -1, :])
            else:
                draft_logits_list = [model_logits[:, i, :] for i in range(self.draft_steps)]
            verified = 0
            for i in range(self.draft_steps):
                if i >= draft.size(1) - current.size(1):
                    break
                draft_idx = draft.size(1) - self.draft_steps + i
                if draft_idx < current.size(1):
                    continue
                mt = torch.argmax(model_logits[:, draft_idx, :], dim=-1)
                dt = draft[:, draft_idx]
                if mt.item() == dt.item():
                    verified += 1
                else:
                    break
            current = draft[:, : current.size(1) + verified]
            generated.extend(current[0, current.size(1) - verified :].tolist())
            accepted += verified
            if (
                accepted >= params.max_new_tokens
                or (current.size(1) - input_ids.size(1)) >= params.max_new_tokens
            ):
                break
        latency = (time.perf_counter() - start) * 1000.0
        text = tokenizer.decode(generated)
        return GenerationOutput(
            text=text,
            token_ids=generated,
            num_tokens=len(generated),
            finish_reason="length",
            prompt_tokens=input_ids.size(1),
            latency_ms=latency,
        )


def _prepare_input_ids(prompt: str, tokenizer, device: torch.device) -> torch.Tensor:
    ids = tokenizer.encode(prompt).ids if hasattr(tokenizer, "encode") else tokenizer.encode(prompt)
    return torch.tensor(ids, dtype=torch.long, device=device).unsqueeze(0)


class InferenceEngine:
    def __init__(
        self,
        model: nn.Module,
        tokenizer,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device or next(model.parameters()).device
        self.dtype = dtype or next(model.parameters()).dtype
        self.model.eval()
        self.kv_cache = PagedKVCache(
            num_layers=model.num_hidden_layers,
            num_heads=model.num_attention_heads,
            head_dim=model.hidden_size // model.num_attention_heads,
            device=self.device,
            dtype=self.dtype,
        )

    def _decode_stop(
        self, token_ids: list[int], generated: list[int], stop: list[str] | None
    ) -> tuple[list[int], str]:
        if not stop:
            return generated, "length"
        text = self.tokenizer.decode(generated)
        for s in stop:
            if s in text:
                cut = text.index(s)
                return generated[:cut], "stop"
        return generated, "length"

    def generate(
        self, prompt: str, params: SamplingParams | None = None, seq_id: str | None = None
    ) -> GenerationOutput:
        params = params or SamplingParams()
        seq_id = seq_id or str(uuid.uuid4())
        start = time.perf_counter()
        input_ids = _prepare_input_ids(prompt, self.tokenizer, self.device)
        self.kv_cache.reset()
        self.kv_cache.allocate(seq_id, input_ids.size(1))
        generated: list[int] = []
        current = input_ids
        for _step in range(params.max_new_tokens):
            with torch.no_grad():
                out = self.model(current)
            logits = out["logits"][:, -1, :]
            next_t, _ = _sample(logits, params, generated)
            token_id = next_t.item()
            generated.append(token_id)
            current = torch.cat([current, next_t], dim=1)
            if token_id == self.tokenizer.token_to_id("<eos>"):
                break
        generated, reason = self._decode_stop(prompt, generated, params.stop)
        latency = (time.perf_counter() - start) * 1000.0
        text = self.tokenizer.decode(generated)
        return GenerationOutput(
            text=text,
            token_ids=generated,
            num_tokens=len(generated),
            finish_reason=reason,
            prompt_tokens=input_ids.size(1),
            latency_ms=latency,
        )

    async def astream_generate(
        self, prompt: str, params: SamplingParams | None = None, seq_id: str | None = None
    ) -> AsyncIterator[str]:
        params = params or SamplingParams()
        seq_id = seq_id or str(uuid.uuid4())
        input_ids = _prepare_input_ids(prompt, self.tokenizer, self.device)
        self.kv_cache.reset()
        self.kv_cache.allocate(seq_id, input_ids.size(1))
        generated: list[int] = []
        current = input_ids
        for _ in range(params.max_new_tokens):
            with torch.no_grad():
                out = self.model(current)
            logits = out["logits"][:, -1, :]
            next_t, _ = _sample(logits, params, generated)
            token_id = next_t.item()
            generated.append(token_id)
            current = torch.cat([current, next_t], dim=1)
            token_str = self.tokenizer.decode([token_id])
            yield token_str
            if token_id == self.tokenizer.token_to_id("<eos>"):
                break

    def stream_generate(self, prompt: str, params: SamplingParams | None = None) -> Iterator[str]:
        asyncio.get_event_loop()

        async def _gen():
            async for chunk in self.astream_generate(prompt, params):
                yield chunk

        return _gen()

    def beam_search(
        self, prompt: str, beam_width: int = 4, max_new_tokens: int = 100
    ) -> GenerationOutput:
        input_ids = _prepare_input_ids(prompt, self.tokenizer, self.device)
        start = time.perf_counter()
        beams = [(input_ids, 0.0)]
        completed: list[tuple[torch.Tensor, float]] = []
        eos_id = self.tokenizer.token_to_id("<eos>")
        for _ in range(max_new_tokens):
            new_beams: list[tuple[torch.Tensor, float]] = []
            for seq, score in beams:
                with torch.no_grad():
                    out = self.model(seq)
                logits = out["logits"][:, -1, :]
                log_probs = F.log_softmax(logits, dim=-1)
                top_scores, top_ids = torch.topk(log_probs, beam_width, dim=-1)
                for i in range(beam_width):
                    token_id = top_ids[0, i].item()
                    token_score = top_scores[0, i].item()
                    new_seq = torch.cat([seq, top_ids[:, i : i + 1]], dim=1)
                    new_score = score + token_score
                    if token_id == eos_id:
                        completed.append((new_seq, new_score))
                    else:
                        new_beams.append((new_seq, new_score))
            beams = sorted(new_beams, key=lambda x: x[1])[:beam_width]
            if not beams and completed:
                break
        if not completed and beams:
            completed.extend(beams)
        if not completed:
            raise InferenceError("Beam search produced no sequences")
        best_seq, best_score = max(completed, key=lambda x: x[1])
        text = self.tokenizer.decode(best_seq[0, input_ids.size(1) :].tolist())
        latency = (time.perf_counter() - start) * 1000.0
        return GenerationOutput(
            text=text,
            token_ids=best_seq[0, input_ids.size(1) :].tolist(),
            num_tokens=best_seq.size(1) - input_ids.size(1),
            finish_reason="length",
            prompt_tokens=input_ids.size(1),
            latency_ms=latency,
        )

    def batch_generate(
        self, prompts: list[str], params: SamplingParams | None = None
    ) -> list[GenerationOutput]:
        params = params or SamplingParams()
        results = []
        for prompt in prompts:
            results.append(self.generate(prompt, params))
        return results

    def chat(
        self, messages: list[dict[str, str]], params: SamplingParams | None = None
    ) -> GenerationOutput:
        params = params or SamplingParams()
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        return self.generate(prompt, params)

    def completion(self, prompt: str, params: SamplingParams | None = None) -> GenerationOutput:
        return self.generate(prompt, params)

    def count_tokens(self, text: str) -> int:
        ids = (
            self.tokenizer.encode(text).ids
            if hasattr(self.tokenizer, "encode")
            else self.tokenizer.encode(text)
        )
        return len(ids)


def _format_openai_chunk(data: dict[str, Any]) -> str:
    return json.dumps(data) + "\n"


def _format_openai_response(
    output: GenerationOutput, model: str = "astrovox", prompt: str = ""
) -> dict[str, Any]:
    return {
        "id": f"cmpl-{uuid.uuid4().hex[:24]}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "prompt": prompt,
        "choices": [
            {
                "index": 0,
                "text": output.text,
                "finish_reason": output.finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": output.prompt_tokens,
            "completion_tokens": output.num_tokens,
            "total_tokens": output.prompt_tokens + output.num_tokens,
        },
    }


class CompletionRequest(BaseModel):
    prompt: str
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)
    stop: list[str] | None = None
    stream: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)
    stop: list[str] | None = None
    stream: bool = False


class BatchRequest(BaseModel):
    prompts: list[str]
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)


def create_app(
    engine: InferenceEngine | None = None,
    config_path: str | None = None,
    checkpoint_path: str | None = None,
    device: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Astrovox Inference Engine", version="10.0.0")

    if engine is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        llm_root = os.path.abspath(os.path.join(base_dir, ".."))
        config_path = config_path or os.path.join(llm_root, "configs", "config_4b.yaml")
        checkpoint_path = checkpoint_path or os.path.join(llm_root, "model.pt")
        config = load_config(config_path)
        dev = device or get_device()
        if dev == "cpu":
            set_cpu_threads(min(4, os.cpu_count() or 2))
        dtype = (
            torch.bfloat16
            if config.get("mixed_precision") == "bf16" and dev != "cuda"
            else torch.float32
        )
        if dev == "cuda" and config.get("mixed_precision") == "fp16":
            dtype = torch.float16
        model = LLM(config, device=torch.device(dev), dtype=dtype)
        if os.path.exists(checkpoint_path):
            model.load_state_dict(torch.load(checkpoint_path, map_location=dev, weights_only=True))
        tokenizer = load_tokenizer(
            config.get("tokenizer_path", os.path.join(llm_root, "tokenizer.json"))
        )
        engine = InferenceEngine(model, tokenizer, device=torch.device(dev), dtype=dtype)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/v1/completions")
    async def completions(req: CompletionRequest):
        with LATENCY_HISTOGRAM.labels("completions").time():
            params = SamplingParams(
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_k=req.top_k,
                top_p=req.top_p,
                repetition_penalty=req.repetition_penalty,
                stop=req.stop,
            )
            try:
                if req.stream:

                    async def _stream():
                        async for chunk in engine.astream_generate(req.prompt, params):
                            data = {"choices": [{"text": chunk, "index": 0}]}
                            yield _format_openai_chunk(data)
                        yield "data: [DONE]\n\n"

                    return StreamingResponse(_stream(), media_type="text/event-stream")
                output = engine.generate(req.prompt, params)
                REQUEST_COUNTER.labels("completions", "success").inc()
                return _format_openai_response(output, prompt=req.prompt)
            except Exception as exc:
                REQUEST_COUNTER.labels("completions", "error").inc()
                raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatCompletionRequest):
        with LATENCY_HISTOGRAM.labels("chat").time():
            params = SamplingParams(
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_k=req.top_k,
                top_p=req.top_p,
                repetition_penalty=req.repetition_penalty,
                stop=req.stop,
            )
            messages = [m.model_dump() for m in req.messages]
            try:
                if req.stream:

                    async def _stream():
                        async for chunk in engine.astream_generate(
                            "\n".join(f"{m['role']}: {m['content']}" for m in messages), params
                        ):
                            data = {"choices": [{"delta": {"content": chunk}, "index": 0}]}
                            yield _format_openai_chunk(data)
                        yield "data: [DONE]\n\n"

                    return StreamingResponse(_stream(), media_type="text/event-stream")
                output = engine.chat(messages, params)
                REQUEST_COUNTER.labels("chat", "success").inc()
                prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                return _format_openai_response(output, model="astrovox-chat", prompt=prompt)
            except Exception as exc:
                REQUEST_COUNTER.labels("chat", "error").inc()
                raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/v1/batch")
    async def batch(req: BatchRequest):
        with LATENCY_HISTOGRAM.labels("batch").time():
            params = SamplingParams(
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_k=req.top_k,
                top_p=req.top_p,
                repetition_penalty=req.repetition_penalty,
            )
            try:
                outputs = engine.batch_generate(req.prompts, params)
                REQUEST_COUNTER.labels("batch", "success").inc()
                return {
                    "results": [
                        {"text": o.text, "tokens": o.num_tokens, "latency_ms": o.latency_ms}
                        for o in outputs
                    ]
                }
            except Exception as exc:
                REQUEST_COUNTER.labels("batch", "error").inc()
                raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/metrics")
    async def metrics():
        from fastapi.responses import Response
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    config_path: str | None = None,
    checkpoint_path: str | None = None,
    device: str | None = None,
):
    import uvicorn

    app = create_app(config_path=config_path, checkpoint_path=checkpoint_path, device=device)
    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="Astrovox Phase 10 Inference Engine")
    parser.add_argument("--config", default=None)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--max-tokens", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--beam-width", type=int, default=0)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--chat", action="store_true")
    args = parser.parse_args()
    if args.serve:
        run_server(
            host=args.host,
            port=args.port,
            config_path=args.config,
            checkpoint_path=args.checkpoint,
            device=args.device,
        )
        return
    base_dir = os.path.dirname(os.path.abspath(__file__))
    llm_root = os.path.abspath(os.path.join(base_dir, ".."))
    config_path = args.config or os.path.join(llm_root, "configs", "config_4b.yaml")
    checkpoint_path = args.checkpoint or os.path.join(llm_root, "model.pt")
    config = load_config(config_path)
    dev = args.device or get_device()
    if dev == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))
    dtype = (
        torch.bfloat16
        if config.get("mixed_precision") == "bf16" and dev != "cuda"
        else torch.float32
    )
    if dev == "cuda" and config.get("mixed_precision") == "fp16":
        dtype = torch.float16
    model = LLM(config, device=torch.device(dev), dtype=dtype)
    if os.path.exists(checkpoint_path):
        model.load_state_dict(torch.load(checkpoint_path, map_location=dev, weights_only=True))
    tokenizer = load_tokenizer(
        config.get("tokenizer_path", os.path.join(llm_root, "tokenizer.json"))
    )
    engine = InferenceEngine(model, tokenizer, device=torch.device(dev), dtype=dtype)
    if args.chat:
        from .chat import chat_loop

        chat_loop(model, tokenizer, dev)
        return
    if not args.prompt:
        print(
            "Provide --prompt for single-shot generation, --chat for interactive mode, or --serve to start the API server."
        )
        return
    params = SamplingParams(
        max_new_tokens=args.max_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        repetition_penalty=args.repetition_penalty,
    )
    if args.beam_width and args.beam_width > 0:
        output = engine.beam_search(
            args.prompt, beam_width=args.beam_width, max_new_tokens=args.max_tokens
        )
    else:
        output = engine.generate(args.prompt, params)
    print(output.text)


if __name__ == "__main__":
    main()
