from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Reflection Module
# ---------------------------------------------------------------------------


class ReflectionModule(nn.Module):
    """Self-reflection module generating critiques of outputs."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 4,
        num_attention_heads: int = 12,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=num_attention_heads, batch_first=True,
            device=device, dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.critique_head = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self.score_head = nn.Linear(hidden_size, 1, device=device, dtype=dtype)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.embedding(input_ids)
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        x = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        x = self.ln(x)
        if attention_mask is not None:
            lengths = attention_mask.sum(dim=1, keepdim=True)
            pooled = (x * attention_mask.unsqueeze(-1)).sum(dim=1) / lengths.clamp(min=1)
        else:
            pooled = x.mean(dim=1)
        critique = self.critique_head(pooled)
        score = self.score_head(pooled).squeeze(-1)
        return critique, score


# ---------------------------------------------------------------------------
# 2. Self-Critique Module
# ---------------------------------------------------------------------------


class SelfCritiqueModule(nn.Module):
    """Generates self-critique and improvement suggestions."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_layers: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.critique_net = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
        )
        self.improvement_head = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self.confidence_head = nn.Linear(hidden_size, 1, device=device, dtype=dtype)

    def forward(
        self,
        original_output: torch.Tensor,
        reflection: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        combined = torch.cat([original_output, reflection], dim=-1)
        critique = self.critique_net(combined)
        improvement = self.improvement_head(critique)
        confidence = torch.sigmoid(self.confidence_head(critique)).squeeze(-1)
        return improvement, confidence


# ---------------------------------------------------------------------------
# 3. Iterative Improvement Loop
# ---------------------------------------------------------------------------


@dataclass
class ImprovementResult:
    original: str
    critique: str
    improved: str
    confidence: float
    iterations: int


class SelfImprovingAgent:
    """Agent that iteratively improves its outputs using self-reflection."""

    def __init__(
        self,
        model: nn.Module,
        reflection_model: ReflectionModule,
        critique_model: SelfCritiqueModule,
        tokenizer: object,
        max_iterations: int = 4,
        confidence_threshold: float = 0.8,
        device: torch.device | None = None,
    ):
        self.model = model
        self.reflection_model = reflection_model
        self.critique_model = critique_model
        self.tokenizer = tokenizer
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.device = device or next(model.parameters()).device

    def improve(self, prompt: str) -> ImprovementResult:
        current_output = self._generate(prompt)
        original = current_output
        for iteration in range(self.max_iterations):
            input_ids = self._encode(current_output)
            critique_vec, score = self.reflection_model(input_ids)
            improvement_vec, confidence = self.critique_model(
                self._encode(current_output).float().mean(dim=1), critique_vec
            )
            if confidence.mean() >= self.confidence_threshold:
                break
            current_output = self._apply_improvement(prompt, current_output, improvement_vec)
        return ImprovementResult(
            original=original,
            critique=self._decode(critique_vec),
            improved=current_output,
            confidence=float(confidence.mean().item()),
            iterations=iteration + 1,
        )

    def _generate(self, prompt: str) -> str:
        inputs = self._encode(prompt)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=512, temperature=0.7)
        return self._decode(outputs)

    def _apply_improvement(self, prompt: str, current: str, improvement: torch.Tensor) -> str:
        improved_prompt = f"{prompt}\n\nPrevious output:\n{current}\n\nCritique:\n{self._decode(improvement.unsqueeze(0))}\n\nImproved output:"
        return self._generate(improved_prompt)

    def _encode(self, text: str) -> torch.Tensor:
        if hasattr(self.tokenizer, "encode"):
            return torch.tensor(
                [self.tokenizer.encode(text)], device=self.device, dtype=torch.long
            )
        return torch.zeros(1, 1, device=self.device, dtype=torch.long)

    def _decode(self, outputs: torch.Tensor) -> str:
        if hasattr(self.tokenizer, "decode"):
            return self.tokenizer.decode(outputs[0].tolist())
        return " ".join(str(tok) for tok in outputs[0].tolist())


# ---------------------------------------------------------------------------
# 4. Meta-Learning Reflection
# ---------------------------------------------------------------------------


class MetaReflection(nn.Module):
    """Meta-learning layer that learns to reflect on task performance."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_tasks: int = 10,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.task_embedding = nn.Embedding(num_tasks, hidden_size, device=device, dtype=dtype)
        self.reflection_net = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
        )
        self.task_adaptation = nn.Sequential(
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
        )

    def forward(
        self,
        hidden_states: torch.Tensor,
        task_id: int,
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        task_emb = self.task_embedding(torch.tensor([task_id], device=hidden_states.device))
        task_emb = task_emb.unsqueeze(0).expand(B, T, -1)
        combined = torch.cat([hidden_states, task_emb], dim=-1)
        reflection = self.reflection_net(combined)
        adapted = self.task_adaptation(reflection)
        return hidden_states + adapted
