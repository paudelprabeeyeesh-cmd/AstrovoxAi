"""
Real Inference Engine - replaces simulated inference_engine.py.

Implements actual token generation using the real transformer model.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

import torch

from app.model import AstroVoxModel

logger = logging.getLogger(__name__)


@dataclass
class KVCachePage:
    page_id: str
    token_start: int
    token_end: int
    memory_offset: int
    size_bytes: int


@dataclass
class KVCache:
    seq_len: int
    page_size: int = 16
    pages: list = field(default_factory=list)
    page_table: dict = field(default_factory=dict)

    def allocate(self) -> int:
        import uuid
        num_pages = (self.seq_len + self.page_size - 1) // self.page_size
        for i in range(num_pages):
            page = KVCachePage(
                page_id=str(uuid.uuid4()),
                token_start=i * self.page_size,
                token_end=min((i + 1) * self.page_size, self.seq_len),
                memory_offset=i * self.page_size * 512,
                size_bytes=self.page_size * 512,
            )
            self.pages.append(page)
            self.page_table[i] = page
        return num_pages

    def get_memory_usage(self) -> dict:
        total_bytes = sum(p.size_bytes for p in self.pages)
        return {
            "num_pages": len(self.pages),
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "page_table": {k: {"page_id": v.page_id, "offset": v.memory_offset} for k, v in self.page_table.items()},
        }


class InferenceAdapter:
    """Real inference adapter using AstroVoxModel."""

    def __init__(self, model: Optional[AstroVoxModel] = None, model_name: str = "astrovox-1b"):
        self.model_name = model_name
        self.model = model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.model is not None:
            self.model = self.model.to(self.device)
            self.model.eval()

    def load_model(self, model_path: str):
        """Load model from state_dict file."""
        state = torch.load(model_path, map_location=self.device)
        if isinstance(state, dict) and "model_state_dict" in state:
            state = state["model_state_dict"]
        if self.model is None:
            raise RuntimeError("Model architecture must be created before loading weights")
        self.model.load_state_dict(state)
        self.model = self.model.to(self.device)
        self.model.eval()

    def save_model(self, model_path: str):
        """Save model state_dict."""
        if self.model is None:
            raise RuntimeError("No model to save")
        torch.save({"model_state_dict": self.model.state_dict()}, model_path)

    def prefill(self, input_ids: list, kv_cache: Optional[KVCache] = None) -> dict:
        """Run prefill pass on input tokens."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        input_tensor = torch.tensor([input_ids], device=self.device)
        start = time.perf_counter()
        with torch.no_grad():
            logits = self.model(input_tensor)
        ttft = time.perf_counter() - start
        return {
            "logits_shape": list(logits.shape),
            "time_to_first_token_ms": round(ttft * 1000, 2),
            "kv_cache_pages": kv_cache.get_memory_usage()["num_pages"] if kv_cache else 0,
        }

    def decode(self, input_ids: list, max_new_tokens: int = 32, temperature: float = 0.7, top_p: float = 0.95, top_k: int = 50) -> List[int]:
        """Generate tokens using real model with sampling."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        generated = []
        input_tensor = torch.tensor([input_ids], device=self.device)
        for _ in range(max_new_tokens):
            with torch.no_grad():
                logits = self.model(input_tensor)
            next_logits = logits[0, -1, :]
            next_token = sample_token(next_logits, temperature=temperature, top_p=top_p, top_k=top_k)
            generated.append(next_token)
            input_tensor = torch.cat([input_tensor, torch.tensor([[next_token]], device=self.device)], dim=1)
        return generated

    def batch_admit(self, requests: list, batch_id: str) -> dict:
        """Admit requests for batch processing."""
        return {
            "batch_id": batch_id,
            "active_count": len(requests),
            "queued_count": 0,
        }


@torch.no_grad()
def sample_token(logits: torch.Tensor, temperature: float = 0.7, top_p: float = 0.95, top_k: int = 50, min_p: Optional[float] = None) -> int:
    """Sample a token from logits with temperature, top-k, top-p, min-p."""
    if temperature <= 0:
        return int(torch.argmax(logits).item())
    logits = logits / temperature
    if top_k > 0:
        top_k = min(top_k, logits.size(-1))
        topk_vals, topk_idx = torch.topk(logits, top_k)
        mask = torch.full_like(logits, float("-inf"))
        mask[topk_idx] = logits[topk_idx]
        logits = mask
    if top_p < 1.0:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        cumulative = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
        sorted_mask = cumulative > top_p
        sorted_mask[1:] = sorted_mask[1:] & sorted_mask[:-1]
        mask = torch.full_like(logits, float("-inf"))
        mask[sorted_idx[sorted_mask]] = float("-inf")
        mask[sorted_idx[~sorted_mask]] = logits[sorted_idx[~sorted_mask]]
        logits = mask
    if min_p is not None:
        max_logit = logits.max()
        min_logit = max_logit - min_p
        logits = torch.where(logits < min_logit, torch.tensor(float("-inf"), device=logits.device), logits)
    probs = torch.softmax(logits, dim=-1)
    return int(torch.multinomial(probs, 1).item())


@torch.no_grad()
def beam_search(model: AstroVoxModel, input_ids: torch.Tensor, beam_size: int = 4, max_new_tokens: int = 32, length_penalty: float = 1.0) -> List[tuple]:
    """Beam search with length normalization."""
    batch_size, seq_len = input_ids.shape
    device = input_ids.device
    sequences = input_ids.repeat(beam_size, 1)
    scores = torch.zeros(beam_size, device=device)
    finished = torch.zeros(beam_size, dtype=torch.bool, device=device)
    finished_scores = []
    finished_seqs = []
    for _ in range(max_new_tokens):
        logits = model(sequences)
        next_logits = logits[:, -1, :]
        probs = torch.softmax(next_logits, dim=-1)
        log_probs = torch.log(probs + 1e-10)
        if finished.any():
            log_probs[finished] = 0
        expanded_scores = scores.unsqueeze(1) + log_probs
        flat_scores = expanded_scores.view(-1)
        num_tokens = min(beam_size * 2, flat_scores.numel())
        top_scores, top_indices = torch.topk(flat_scores, num_tokens)
        beam_indices = top_indices // next_logits.size(-1)
        token_indices = top_indices % next_logits.size(-1)
        new_sequences = []
        new_scores = []
        new_finished = []
        for i in range(num_tokens):
            b_idx = beam_indices[i].item()
            t_idx = token_indices[i].item()
            score = top_scores[i].item()
            seq = torch.cat([sequences[b_idx], torch.tensor([t_idx], device=device)])
            is_finished = finished[b_idx].item() or t_idx == 2  # EOS
            if is_finished:
                norm_score = score / (seq.shape[0] ** length_penalty)
                finished_scores.append(norm_score)
                finished_seqs.append(seq.cpu().tolist())
            else:
                new_sequences.append(seq)
                new_scores.append(score)
                new_finished.append(is_finished)
        if not new_sequences:
            break
        sequences = torch.stack(new_sequences)
        scores = torch.tensor(new_scores, device=device)
        finished = torch.tensor(new_finished, dtype=torch.bool, device=device)
    all_results = [(seq, score) for seq, score in zip(finished_seqs, finished_scores)]
    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results[:beam_size]
