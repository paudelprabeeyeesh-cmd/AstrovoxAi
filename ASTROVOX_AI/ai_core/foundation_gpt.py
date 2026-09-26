import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
import math
import os

from .transformers.transformer_from_scratch import TransformerFromScratch, TransformerConfig

logger = logging.getLogger(__name__)


@dataclass
class GPTConfig:
    vocab_size: int = 50257
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    intermediate_size: int = 3072
    max_position_embeddings: int = 1024
    dropout: float = 0.1
    activation: str = "gelu"
    initializer_range: float = 0.02
    tie_word_embeddings: bool = True


class GPTModel(nn.Module):
    def __init__(self, config: Optional[GPTConfig] = None):
        super().__init__()
        self.config = config or GPTConfig()
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

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)

    def forward(self, input_ids, labels=None, attention_mask=None):
        logits = self.transformer(input_ids)
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        return {"logits": logits, "loss": loss}

    @torch.no_grad()
    def generate(self, input_ids, max_length=100, temperature=1.0, top_k=None, top_p=None):
        self.eval()
        for _ in range(max_length - input_ids.size(1)):
            logits = self.transformer(input_ids)
            logits = logits[:, -1, :] / max(temperature, 1e-8)
            if top_k is not None:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float('-inf')
            probs = F.softmax(logits, dim=-1)
            if top_p is not None:
                sorted_probs, sorted_indices = torch.sort(probs, descending=True)
                cumulative_probs = torch.cumsum(sorted_probs, dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = False
                indices_to_remove = sorted_indices[sorted_indices_to_remove]
                probs[:, indices_to_remove] = 0.0
            next_token = torch.multinomial(probs, num_samples=1)
            input_ids = torch.cat([input_ids, next_token], dim=1)
        return input_ids


class GPTTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        self.step = 0
        self.epoch = 0
        logger.info("GPTTrainer initialized on %s", self.device)

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

    def train_epoch(self, dataloader):
        total_loss = 0.0
        steps = 0
        for batch in dataloader:
            result = self.train_step(batch)
            total_loss += result["loss"]
            steps += 1
        self.epoch += 1
        avg_loss = total_loss / max(steps, 1)
        logger.info("Epoch %d complete, avg loss: %.4f", self.epoch, avg_loss)
        return {"loss": avg_loss, "epoch": self.epoch, "steps": steps}

    def evaluate(self, dataloader):
        self.model.eval()
        total_loss = 0.0
        steps = 0
        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch.get("labels", input_ids).to(self.device)
                outputs = self.model(input_ids, labels=labels)
                total_loss += outputs["loss"].item()
                steps += 1
        avg_loss = total_loss / max(steps, 1)
        logger.info("Evaluation complete, avg loss: %.4f", avg_loss)
        return {"loss": avg_loss, "epoch": self.epoch}

    def save_checkpoint(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "step": self.step,
            "epoch": self.epoch,
            "config": self.model.config,
        }, path)
        logger.info("Checkpoint saved to %s", path)

    def load_checkpoint(self, path: str):
        ckpt = torch.load(path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        self.step = ckpt.get("step", 0)
        self.epoch = ckpt.get("epoch", 0)
        logger.info("Checkpoint loaded from %s", path)
