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
class InstructionConfig:
    vocab_size: int = 50257
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    intermediate_size: int = 3072
    max_position_embeddings: int = 2048
    dropout: float = 0.1
    tie_word_embeddings: bool = True


class InstructionModel(nn.Module):
    def __init__(self, config: Optional[InstructionConfig] = None):
        super().__init__()
        self.config = config or InstructionConfig()
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
        logger.info("InstructionModel initialized")

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

    def forward(self, input_ids, labels=None):
        logits = self.transformer(input_ids)
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        return {"logits": logits, "loss": loss}


class InstructionTuner:
    def __init__(self, model, config: Optional[InstructionConfig] = None):
        self.model = model
        self.config = config or InstructionConfig()
        logger.info("InstructionTuner initialized")

    def format_example(self, instruction, input_text="", output_text=""):
        if input_text:
            prompt = f"Instruction: {instruction}\nInput: {input_text}\nResponse:"
        else:
            prompt = f"Instruction: {instruction}\nResponse:"
        return prompt, output_text

    def train_step(self, batch):
        return {"loss": 0.0}


class InstructionTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        self.step = 0
        logger.info("InstructionTrainer initialized")

    def train_step(self, batch):
        self.model.train()
        input_ids = batch["input_ids"].to(self.device)
        labels = batch.get("labels", input_ids).to(self.device)
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
