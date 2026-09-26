import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import os

from .transformers.transformer_from_scratch import TransformerFromScratch, TransformerConfig

logger = logging.getLogger(__name__)


@dataclass
class CodeModelConfig:
    vocab_size: int = 50000
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    intermediate_size: int = 3072
    max_position_embeddings: int = 2048
    dropout: float = 0.1
    tie_word_embeddings: bool = True


class CodeModel(nn.Module):
    def __init__(self, config: Optional[CodeModelConfig] = None):
        super().__init__()
        self.config = config or CodeModelConfig()
        t_config = TransformerConfig(
            vocab_size=self.config.vocab_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            num_heads=self.config.num_heads,
            intermediate_size=self.config.intermediate_size,
            max_position_embeddings=self.config.max_position_embeddings,
            dropout=self.config.dropout,
        )
        self.transformer = TransformerFromScratch(t_config)
        self.lm_head = nn.Linear(self.config.hidden_size, self.config.vocab_size, bias=False)
        if self.config.tie_word_embeddings:
            self.lm_head.weight = self.transformer.token_emb.weight
        self.apply(self._init_weights)
        logger.info("CodeModel initialized")

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.trunc_normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)

    def forward(self, code_tokens, labels=None):
        logits = self.transformer(code_tokens)
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1), ignore_index=-100)
        return {"logits": logits, "loss": loss}

    def complete(self, prompt, max_length: int = 100):
        return self.generate(prompt, max_length=max_length)

    @torch.no_grad()
    def generate(self, input_ids, max_length=100, temperature=1.0, top_k=None):
        self.eval()
        for _ in range(max_length - input_ids.size(1)):
            logits = self.transformer(input_ids)
            logits = logits[:, -1, :] / max(temperature, 1e-8)
            if top_k is not None:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float('-inf')
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_token], dim=1)
        return input_ids


class CodeModelTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.05)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        self.step = 0
        logger.info("CodeModelTrainer initialized")

    def train_step(self, code_batch):
        self.model.train()
        input_ids = code_batch["input_ids"].to(self.device)
        labels = code_batch.get("labels", input_ids).to(self.device)
        outputs = self.model(input_ids, labels=labels)
        loss = outputs["loss"]
        loss.backward()
        if self.grad_clip > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        self.optimizer.zero_grad()
        self.step += 1
        return {"loss": loss.item(), "step": self.step}
