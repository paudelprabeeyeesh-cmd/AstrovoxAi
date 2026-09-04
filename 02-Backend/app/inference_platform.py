"""
High-performance inference platform (Stage 40 Program 5).

Implements:
  * Continuous batching (vLLM-style request scheduling)
  * Speculative decoding primitives
  * Multi-model routing
  * GPU-aware autoscaling hints
  * Streaming inference support
  * Token-by-token generation
"""

from __future__ import annotations

import asyncio
import heapq
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Awaitable, Callable, Deque, Dict, List, Optional, Tuple

from .security_hardening import AuditLog, get_audit_log


class RequestState(str, Enum):
    PENDING = "pending"
    PREFILLING = "prefilling"
    DECODING = "decoding"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class GenerationRequest:
    id: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 1.0
    top_p: float = 1.0
    stop_tokens: List[str] = field(default_factory=list)
    state: RequestState = RequestState.PENDING
    tokens_generated: int = 0
    output: str = ""
    queued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    model_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt_length": len(self.prompt),
            "max_tokens": self.max_tokens,
            "tokens_generated": self.tokens_generated,
            "output": self.output,
            "state": self.state.value,
            "model_id": self.model_id,
            "error": self.error,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


# ---------------------------------------------------------------------------
# Continuous batching
# ---------------------------------------------------------------------------


class ContinuousBatchScheduler:
    """Token-budget-based continuous batcher.

    Requests are accumulated in a queue. When the batch reaches the
    configured max batch size or max tokens, all queued requests are
    forwarded to the model together. Finished requests are removed
    from the active batch, allowing new requests to enter.
    """

    def __init__(
        self,
        model_executor: Callable[[List[GenerationRequest]], Awaitable[List[str]]],
        *,
        max_batch_size: int = 32,
        max_batch_tokens: int = 8192,
        max_wait_ms: float = 10.0,
    ) -> None:
        self.model_executor = model_executor
        self.max_batch_size = max_batch_size
        self.max_batch_tokens = max_batch_tokens
        self.max_wait_ms = max_wait_ms
        self._queue: Deque[GenerationRequest] = deque()
        self._active: Dict[str, GenerationRequest] = {}
        self._lock = asyncio.Lock()
        self._audit: AuditLog = get_audit_log()
        self._total_processed = 0
        self._total_tokens_generated = 0

    async def submit(self, request: GenerationRequest) -> GenerationRequest:
        request.state = RequestState.PENDING
        async with self._lock:
            self._queue.append(request)
        return request

    async def cancel(self, request_id: str) -> bool:
        async with self._lock:
            for req in self._queue:
                if req.id == request_id:
                    req.state = RequestState.CANCELLED
                    self._queue.remove(req)
                    return True
            if request_id in self._active:
                self._active[request_id].state = RequestState.CANCELLED
                return True
        return False

    async def step(self) -> List[GenerationRequest]:
        """Run one scheduling step: take a batch from the queue, execute, return finished."""
        async with self._lock:
            batch: List[GenerationRequest] = []
            total_tokens = 0
            while self._queue and len(batch) < self.max_batch_size:
                req = self._queue.popleft()
                prompt_tokens = len(req.prompt.split())
                if total_tokens + prompt_tokens > self.max_batch_tokens and batch:
                    self._queue.appendleft(req)
                    break
                batch.append(req)
                total_tokens += prompt_tokens
                self._active[req.id] = req

        if not batch:
            return []

        # Wait up to max_wait_ms for more requests (continuous batching)
        try:
            await asyncio.wait_for(self._wait_for_more(), timeout=self.max_wait_ms / 1000.0)
            async with self._lock:
                while self._queue and len(batch) < self.max_batch_size:
                    req = self._queue.popleft()
                    batch.append(req)
                    self._active[req.id] = req
        except asyncio.TimeoutError:
            pass

        # Mark prefill + execute
        for req in batch:
            req.state = RequestState.PREFILLING
            req.started_at = time.time()
        try:
            outputs = await self.model_executor(batch)
        except Exception as exc:
            for req in batch:
                req.state = RequestState.FAILED
                req.error = str(exc)
                req.finished_at = time.time()
                async with self._lock:
                    self._active.pop(req.id, None)
            self._audit.record(
                actor="batcher",
                action="batch_failed",
                target="continuous_batcher",
                outcome="failed",
                metadata={"batch_size": len(batch), "error": str(exc)},
            )
            return batch

        finished: List[GenerationRequest] = []
        for req, output in zip(batch, outputs):
            req.output = output
            req.tokens_generated = len(output.split())
            req.state = RequestState.FINISHED
            req.finished_at = time.time()
            async with self._lock:
                self._active.pop(req.id, None)
            finished.append(req)
            self._total_processed += 1
            self._total_tokens_generated += req.tokens_generated
        return finished

    async def _wait_for_more(self) -> None:
        async with self._lock:
            if not self._queue:
                await asyncio.sleep(0.001)

    async def run_until_empty(self, max_steps: int = 1000) -> List[GenerationRequest]:
        finished: List[GenerationRequest] = []
        for _ in range(max_steps):
            async with self._lock:
                if not self._queue and not self._active:
                    break
            step_finished = await self.step()
            finished.extend(step_finished)
        return finished

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_size": len(self._queue),
            "active": len(self._active),
            "total_processed": self._total_processed,
            "total_tokens_generated": self._total_tokens_generated,
        }


# ---------------------------------------------------------------------------
# Speculative decoding
# ---------------------------------------------------------------------------


class SpeculativeDecoder:
    """Draft-then-verify speculative decoding.

    A smaller "draft" model proposes K tokens; the larger "target" model
    verifies them in a single forward pass. Accept the longest prefix
    that matches and resample from the next token's distribution.
    """

    def __init__(
        self,
        draft_model: Callable[[List[int], int], List[int]],
        target_model: Callable[[List[int]], List[float]],
        *,
        draft_k: int = 5,
    ) -> None:
        self.draft_model = draft_model
        self.target_model = target_model
        self.draft_k = draft_k

    def propose(self, tokens: List[int]) -> List[int]:
        return self.draft_model(tokens, self.draft_k)

    def verify(self, tokens: List[int], proposed: List[int]) -> Tuple[List[int], int]:
        """Verify proposed tokens. Returns (accepted_tokens, num_accepted)."""
        full = tokens + proposed
        probs = self.target_model(full)
        accepted: List[int] = []
        for i, token in enumerate(proposed):
            token_prob = probs[len(tokens) + i] if len(probs) > len(tokens) + i else 0.0
            if token_prob > 0.01:  # simple threshold
                accepted.append(token)
            else:
                break
        return accepted, len(accepted)

    def decode(self, tokens: List[int], max_new: int = 100) -> List[int]:
        generated: List[int] = []
        while len(generated) < max_new:
            proposed = self.propose(tokens + generated)
            accepted, _ = self.verify(tokens + generated, proposed)
            if not accepted:
                break
            generated.extend(accepted)
        return generated


# ---------------------------------------------------------------------------
# Multi-model routing
# ---------------------------------------------------------------------------


class ModelRouter:
    """Route inference requests to the most appropriate model."""

    def __init__(self) -> None:
        self._models: Dict[str, Dict[str, Any]] = {}
        self._load: Dict[str, int] = {}
        self._lock = threading.Lock()

    def register(
        self,
        model_id: str,
        executor: Callable[..., Awaitable[Any]],
        *,
        cost_per_token: float = 0.001,
        latency_p95_ms: float = 100.0,
        capabilities: Optional[List[str]] = None,
    ) -> None:
        with self._lock:
            self._models[model_id] = {
                "executor": executor,
                "cost_per_token": cost_per_token,
                "latency_p95_ms": latency_p95_ms,
                "capabilities": set(capabilities or []),
            }
            self._load[model_id] = 0

    def route(
        self,
        *,
        request: GenerationRequest,
        preferred_capability: Optional[str] = None,
        prefer_cheapest: bool = True,
    ) -> Optional[str]:
        candidates = list(self._models.keys())
        if preferred_capability:
            candidates = [
                m
                for m in candidates
                if preferred_capability in self._models[m]["capabilities"]
            ]
        if not candidates:
            return None
        if prefer_cheapest:
            candidates.sort(key=lambda m: self._models[m]["cost_per_token"])
        else:
            candidates.sort(key=lambda m: self._load.get(m, 0))
        return candidates[0]

    async def execute(self, model_id: str, request: GenerationRequest) -> Any:
        with self._lock:
            self._load[model_id] = self._load.get(model_id, 0) + 1
        try:
            return await self._models[model_id]["executor"](request)
        finally:
            with self._lock:
                self._load[model_id] = max(0, self._load.get(model_id, 0) - 1)

    def stats(self) -> Dict[str, Any]:
        return {
            "models": {
                mid: {
                    "load": self._load.get(mid, 0),
                    "cost_per_token": m["cost_per_token"],
                    "capabilities": sorted(m["capabilities"]),
                }
                for mid, m in self._models.items()
            }
        }


# ---------------------------------------------------------------------------
# Streaming inference
# ---------------------------------------------------------------------------


class StreamingInference:
    """Token-by-token streaming inference with cancellation support."""

    def __init__(
        self,
        executor: Callable[[List[int], GenerationRequest], AsyncIterator[str]],
    ) -> None:
        self.executor = executor
        self._cancelled: set = set()
        self._lock = threading.Lock()

    def cancel(self, request_id: str) -> None:
        with self._lock:
            self._cancelled.add(request_id)

    async def stream(
        self, request: GenerationRequest, tokens: List[int]
    ) -> AsyncIterator[str]:
        request.state = RequestState.DECODING
        request.started_at = time.time()
        try:
            async for token in self.executor(tokens, request):
                if request.id in self._cancelled:
                    request.state = RequestState.CANCELLED
                    request.finished_at = time.time()
                    return
                request.tokens_generated += 1
                request.output += token
                yield token
                if request.tokens_generated >= request.max_tokens:
                    break
        finally:
            request.finished_at = time.time()
            if request.state not in (
                RequestState.CANCELLED,
                RequestState.FINISHED,
            ):
                request.state = RequestState.FINISHED


# ---------------------------------------------------------------------------
# GPU autoscaling hints
# ---------------------------------------------------------------------------


@dataclass
class ScalingHint:
    current_load: int
    recommended_replicas: int
    reason: str
    cost_estimate_per_hour: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_load": self.current_load,
            "recommended_replicas": self.recommended_replicas,
            "reason": self.reason,
            "cost_estimate_per_hour": round(self.cost_estimate_per_hour, 4),
        }


class GPUScaler:
    """Recommend GPU scaling based on current load and latency targets."""

    def __init__(
        self,
        *,
        max_concurrent_per_gpu: int = 16,
        target_p95_ms: float = 200.0,
        gpu_hourly_cost: float = 2.50,
    ) -> None:
        self.max_concurrent_per_gpu = max_concurrent_per_gpu
        self.target_p95_ms = target_p95_ms
        self.gpu_hourly_cost = gpu_hourly_cost
        self._current_load = 0
        self._current_replicas = 1
        self._current_p95 = 0.0

    def observe(self, *, load: int, p95_ms: float, replicas: int) -> None:
        self._current_load = load
        self._current_p95 = p95_ms
        self._current_replicas = replicas

    def recommend(self) -> ScalingHint:
        capacity = self._current_replicas * self.max_concurrent_per_gpu
        utilization = self._current_load / max(capacity, 1)
        if utilization > 0.85 or self._current_p95 > self.target_p95_ms:
            new_replicas = self._current_replicas + 1
            reason = "high utilization or latency"
        elif utilization < 0.3 and self._current_replicas > 1:
            new_replicas = max(1, self._current_replicas - 1)
            reason = "low utilization"
        else:
            new_replicas = self._current_replicas
            reason = "stable"
        cost = new_replicas * self.gpu_hourly_cost
        return ScalingHint(
            current_load=self._current_load,
            recommended_replicas=new_replicas,
            reason=reason,
            cost_estimate_per_hour=cost,
        )


import threading  # noqa: E402
