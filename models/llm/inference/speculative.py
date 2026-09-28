import logging
import math
import time
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn.functional as F

from .types import GenerationOutput, SamplingParams

logger = logging.getLogger(__name__)


@dataclass
class DraftResult:
    draft_tokens: list[int]
    accepted_tokens: list[int]
    rejected_tokens: list[int]
    draft_latency_ms: float
    verify_latency_ms: float
    acceptance_rate: float


class SpeculativeDecoder:
    def __init__(
        self,
        model,
        draft_model: Optional[torch.nn.Module] = None,
        draft_steps: int = 4,
        device: Optional[torch.device] = None,
    ):
        self.model = model
        self.draft_model = draft_model
        self.draft_steps = draft_steps
        self.device = device or next(model.parameters()).device

    @torch.no_grad()
    def _draft(self, input_ids: torch.Tensor, params: SamplingParams, generated: list[int]) -> tuple[torch.Tensor, list[int]]:
        draft = input_ids
        draft_tokens: list[int] = []
        for _ in range(self.draft_steps):
            if self.draft_model is not None:
                out = self.draft_model(draft)
            else:
                out = self.model(draft)
            logits = out["logits"][:, -1, :]
            next_t, _ = self._sample(logits, params, generated + draft_tokens)
            token_id = next_t.item()
            draft_tokens.append(token_id)
            draft = torch.cat([draft, next_t], dim=1)
        return draft, draft_tokens

    @torch.no_grad()
    def _verify(self, draft: torch.Tensor, original_len: int, params: SamplingParams, generated: list[int]) -> DraftResult:
        out = self.model(draft)
        model_logits = out["logits"]
        accepted: list[int] = []
        rejected: list[int] = []
        for i in range(self.draft_steps):
            draft_idx = original_len + i
            if draft_idx >= draft.size(1):
                break
            model_token = torch.argmax(model_logits[:, draft_idx, :], dim=-1).item()
            draft_token = draft[0, draft_idx].item()
            if model_token == draft_token:
                accepted.append(draft_token)
            else:
                rejected.append(draft_token)
                break
        return DraftResult(
            draft_tokens=[draft[0, original_len + i].item() for i in range(min(self.draft_steps, draft.size(1) - original_len))],
            accepted_tokens=accepted,
            rejected_tokens=rejected,
            draft_latency_ms=0.0,
            verify_latency_ms=0.0,
            acceptance_rate=len(accepted) / self.draft_steps if self.draft_steps else 0.0,
        )

    def _sample(self, logits: torch.Tensor, params: SamplingParams, token_ids: list[int]) -> tuple[torch.Tensor, torch.Tensor]:
        logits = self._apply_repetition_penalty(logits, token_ids, params.repetition_penalty)
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

    def _apply_repetition_penalty(
        self, logits: torch.Tensor, token_ids: list[int], penalty: float
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

    def generate(self, input_ids: torch.Tensor, params: SamplingParams, tokenizer) -> GenerationOutput:
        accepted = 0
        generated: list[int] = []
        current = input_ids
        start = time.perf_counter()
        target = params.max_new_tokens

        while accepted < target:
            draft_start = time.perf_counter()
            draft, draft_tokens = self._draft(current, params, generated)
            draft_latency = (time.perf_counter() - draft_start) * 1000.0

            verify_start = time.perf_counter()
            result = self._verify(draft, current.size(1), params, generated)
            verify_latency = (time.perf_counter() - verify_start) * 1000.0

            result.draft_latency_ms = draft_latency
            result.verify_latency_ms = verify_latency
            logger.debug("Accepted %d/%d draft tokens", len(result.accepted_tokens), self.draft_steps)

            generated.extend(result.accepted_tokens)
            accepted += len(result.accepted_tokens)
            current = draft[:, : current.size(1) + len(result.accepted_tokens)]

            if not result.accepted_tokens:
                with torch.no_grad():
                    out = self.model(current)
                logits = out["logits"][:, -1, :]
                fallback, _ = self._sample(logits, params, generated)
                token_id = fallback.item()
                generated.append(token_id)
                current = torch.cat([current, fallback], dim=1)
                accepted += 1

            if accepted >= target or current.size(1) - input_ids.size(1) >= target:
                break

            eos_id = tokenizer.token_to_id("<eos>")
            if eos_id is not None and generated and generated[-1] == eos_id:
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
