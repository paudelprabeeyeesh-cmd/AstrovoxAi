import json
import logging
import math
import time
import uuid
from collections import OrderedDict
from typing import Any, AsyncIterator, Iterator

import torch
import torch.nn as nn
import torch.nn.functional as F

from .kv_cache import KVCacheBlock, PagedKVCache, PrefixCache
from .scheduler import Request, RequestScheduler
from .speculative import SpeculativeDecoder
from .types import GenerationOutput, InferenceError, InvalidRequestError, SamplingParams

logger = logging.getLogger(__name__)


def _prepare_input_ids(prompt: str, tokenizer, device: torch.device) -> torch.Tensor:
    ids = tokenizer.encode(prompt).ids if hasattr(tokenizer, "encode") else tokenizer.encode(prompt)
    return torch.tensor(ids, dtype=torch.long, device=device).unsqueeze(0)


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


class InferenceEngine:
    def __init__(
        self,
        model: nn.Module,
        tokenizer,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
        enable_prefix_cache: bool = True,
        enable_speculative: bool = False,
        draft_model: nn.Module | None = None,
        draft_steps: int = 4,
        max_blocks: int = 1024,
        block_size: int = 16,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device or next(model.parameters()).device
        self.dtype = dtype or next(model.parameters()).dtype
        self.model.eval()

        num_heads = getattr(model, "num_attention_heads", 1)
        hidden_size = getattr(model, "hidden_size", 1)
        head_dim = hidden_size // num_heads if num_heads else 1
        num_layers = getattr(model, "num_hidden_layers", 1)

        self.kv_cache = PagedKVCache(
            num_layers=num_layers,
            num_heads=num_heads,
            head_dim=head_dim,
            block_size=block_size,
            max_blocks=max_blocks,
            device=self.device,
            dtype=self.dtype,
        )
        self.prefix_cache = PrefixCache() if enable_prefix_cache else None
        self.scheduler = RequestScheduler()
        self._cuda_graph_stub = False

        self.speculative_decoder = None
        if enable_speculative:
            self.speculative_decoder = SpeculativeDecoder(
                model=model,
                draft_model=draft_model,
                draft_steps=draft_steps,
                device=self.device,
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

    def _check_prefix_cache(self, prompt: str) -> tuple[torch.Tensor, int]:
        if self.prefix_cache is None:
            return _prepare_input_ids(prompt, self.tokenizer, self.device), 0
        cached = self.prefix_cache.get(prompt)
        if cached is not None:
            token_ids, _ = cached
            return torch.tensor(token_ids, dtype=torch.long, device=self.device).unsqueeze(0), len(token_ids)
        return _prepare_input_ids(prompt, self.tokenizer, self.device), 0

    def _update_prefix_cache(self, prompt: str, token_ids: list[int]) -> None:
        if self.prefix_cache is not None:
            self.prefix_cache.put(prompt, token_ids)

    def generate(
        self, prompt: str, params: SamplingParams | None = None, seq_id: str | None = None
    ) -> GenerationOutput:
        params = params or SamplingParams()
        seq_id = seq_id or str(uuid.uuid4())
        start = time.perf_counter()

        input_ids, prefix_len = self._check_prefix_cache(prompt)
        prompt_len = input_ids.size(1)

        self.kv_cache.reset()
        self.kv_cache.allocate(seq_id, prompt_len)

        generated: list[int] = []
        current = input_ids
        eos_id = self.tokenizer.token_to_id("<eos>")

        for _step in range(params.max_new_tokens):
            with torch.no_grad():
                out = self.model(current)
            logits = out["logits"][:, -1, :]
            next_t, _ = _sample(logits, params, generated)
            token_id = next_t.item()
            generated.append(token_id)
            current = torch.cat([current, next_t], dim=1)
            if eos_id is not None and token_id == eos_id:
                break

        generated, reason = self._decode_stop(prompt, generated, params.stop)
        all_tokens = input_ids[0].tolist() + generated
        self._update_prefix_cache(prompt, all_tokens)

        latency = (time.perf_counter() - start) * 1000.0
        text = self.tokenizer.decode(generated)
        return GenerationOutput(
            text=text,
            token_ids=generated,
            num_tokens=len(generated),
            finish_reason=reason,
            prompt_tokens=prompt_len,
            latency_ms=latency,
        )

    def continuous_batch_generate(
        self, requests: list[tuple[str, SamplingParams, str]]
    ) -> list[GenerationOutput]:
        results: list[GenerationOutput | None] = [None] * len(requests)
        scheduler = self.scheduler

        for prompt, params, req_id in requests:
            scheduler.submit(Request(id=req_id, prompt=prompt, params=params))

        active_sequences: dict[str, dict[str, Any]] = {}
        finished = 0
        max_steps = max((p.max_new_tokens for _, p, _ in requests), default=100)

        for step in range(max_steps):
            if finished >= len(requests):
                break
            batch = scheduler.next_batch()
            if not batch:
                continue

            batch_ids = []
            batch_prompts = []
            batch_params = []
            for req in batch:
                if req.id not in active_sequences:
                    ids = _prepare_input_ids(req.prompt, self.tokenizer, self.device)
                    self.kv_cache.allocate(req.id, ids.size(1))
                    active_sequences[req.id] = {
                        "current": ids,
                        "generated": [],
                        "params": req.params,
                        "prompt": req.prompt,
                    }
                batch_ids.append(req.id)
                batch_prompts.append(active_sequences[req.id]["current"])
                batch_params.append(active_sequences[req.id]["params"])

            max_len = max(b.size(1) for b in batch_prompts)
            padded = []
            for b in batch_prompts:
                if b.size(1) < max_len:
                    pad = torch.zeros(b.size(0), max_len - b.size(1), dtype=b.dtype, device=b.device)
                    b = torch.cat([b, pad], dim=1)
                padded.append(b)

            batch_tensor = torch.cat(padded, dim=0)
            with torch.no_grad():
                out = self.model(batch_tensor)

            for idx, req_id in enumerate(batch_ids):
                logits = out["logits"][idx : idx + 1, -1, :]
                seq = active_sequences[req_id]
                params = seq["params"]
                next_t, _ = _sample(logits, params, seq["generated"])
                token_id = next_t.item()
                seq["generated"].append(token_id)
                seq["current"] = torch.cat([seq["current"], next_t], dim=1)

                eos_id = self.tokenizer.token_to_id("<eos>")
                if token_id == eos_id or len(seq["generated"]) >= params.max_new_tokens:
                    gen, reason = self._decode_stop(seq["prompt"], seq["generated"], params.stop)
                    text = self.tokenizer.decode(gen)
                    latency = 0.0
                    prompt_tokens = seq["current"].size(1) - len(gen)
                    for i, (_, _, rid) in enumerate(requests):
                        if rid == req_id:
                            results[i] = GenerationOutput(
                                text=text,
                                token_ids=gen,
                                num_tokens=len(gen),
                                finish_reason=reason,
                                prompt_tokens=prompt_tokens,
                                latency_ms=latency,
                            )
                            break
                    self.kv_cache._free_sequence(req_id)
                    active_sequences.pop(req_id, None)
                    finished += 1

        for i, res in enumerate(results):
            if res is None:
                req = requests[i]
                prompt_str, params, req_id = req
                gen, reason = self._decode_stop(prompt_str, [], params.stop)
                results[i] = GenerationOutput(
                    text=self.tokenizer.decode(gen),
                    token_ids=gen,
                    num_tokens=0,
                    finish_reason=reason,
                    prompt_tokens=0,
                    latency_ms=0.0,
                )
        return results

    def stream_generate(
        self, prompt: str, params: SamplingParams | None = None
    ) -> Iterator[str]:
        params = params or SamplingParams()
        input_ids = _prepare_input_ids(prompt, self.tokenizer, self.device)
        seq_id = str(uuid.uuid4())
        self.kv_cache.reset()
        self.kv_cache.allocate(seq_id, input_ids.size(1))
        current = input_ids
        generated: list[int] = []
        for _ in range(params.max_new_tokens):
            with torch.no_grad():
                out = self.model(current)
            logits = out["logits"][:, -1, :]
            next_t, _ = _sample(logits, params, generated)
            token_id = next_t.item()
            generated.append(token_id)
            current = torch.cat([current, next_t], dim=1)
            yield self.tokenizer.decode([token_id])
            if token_id == self.tokenizer.token_to_id("<eos>"):
                break

    async def astream_generate(
        self, prompt: str, params: SamplingParams | None = None, seq_id: str | None = None
    ) -> AsyncIterator[str]:
        for chunk in self.stream_generate(prompt, params):
            yield chunk

    def beam_search(
        self, prompt: str, beam_width: int = 4, max_new_tokens: int = 100
    ) -> GenerationOutput:
        input_ids = _prepare_input_ids(prompt, self.tokenizer, self.device)
        start = time.perf_counter()
        beams: list[tuple[torch.Tensor, float]] = [(input_ids, 0.0)]
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
                    if eos_id is not None and token_id == eos_id:
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
        requests = [(p, params, str(uuid.uuid4())) for p in prompts]
        return self.continuous_batch_generate(requests)

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

    def capture_cuda_graphs(self, dummy_input: torch.Tensor) -> None:
        self._cuda_graph_stub = True
        logger.info("CUDA graph capture requested but not implemented in this build")


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
