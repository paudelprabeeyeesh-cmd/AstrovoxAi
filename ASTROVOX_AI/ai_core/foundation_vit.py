import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
import math
import os

from .transformers.transformer_from_scratch import TransformerConfig, TransformerBlock

logger = logging.getLogger(__name__)


@dataclass
class ViTConfig:
    image_size: int = 224
    patch_size: int = 16
    num_classes: int = 1000
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    mlp_ratio: float = 4.0
    dropout: float = 0.1
    attention_dropout: float = 0.1
    initializer_range: float = 0.02


class ViTModel(nn.Module):
    def __init__(self, config: Optional[ViTConfig] = None):
        super().__init__()
        self.config = config or ViTConfig()
        self.num_patches = (self.config.image_size // self.config.patch_size) ** 2
        self.patch_embed = nn.Conv2d(3, self.config.hidden_size, kernel_size=self.config.patch_size, stride=self.config.patch_size)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, self.config.hidden_size))
        self.pos_embed = nn.Parameter(torch.zeros(1, self.num_patches + 1, self.config.hidden_size))
        self.dropout = nn.Dropout(self.config.dropout)
        t_config = TransformerConfig(
            vocab_size=0,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            num_heads=self.config.num_heads,
            intermediate_size=int(self.config.hidden_size * self.config.mlp_ratio),
            max_position_embeddings=self.num_patches + 1,
            dropout=self.config.dropout,
        )
        self.blocks = nn.ModuleList([TransformerBlock(t_config) for _ in range(self.config.num_layers)])
        self.ln_f = nn.LayerNorm(self.config.hidden_size)
        self.head = nn.Linear(self.config.hidden_size, self.config.num_classes)
        self.apply(self._init_weights)
        logger.info("ViT model initialized with %d patches", self.num_patches)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)
        elif isinstance(module, nn.Conv2d):
            nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=self.config.initializer_range)

    def forward(self, pixels, labels=None):
        B, C, H, W = pixels.shape
        x = self.patch_embed(pixels).flatten(2).transpose(1, 2)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        x = x + self.pos_embed[:, :x.size(1), :]
        x = self.dropout(x)
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.head(x[:, 0])
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits, labels)
        return {"logits": logits, "loss": loss, "hidden_states": x}

    def visualize_attention(self, image):
        return {"attention_map": None}


class ViTTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        self.epoch = 0
        logger.info("ViTTrainer initialized")

    def train_step(self, batch):
        self.model.train()
        pixels = batch["pixels"].to(self.device)
        labels = batch.get("labels")
        if labels is not None:
            labels = labels.to(self.device)
        outputs = self.model(pixels, labels=labels)
        loss = outputs["loss"]
        loss.backward()
        if self.grad_clip > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        self.optimizer.zero_grad()
        return {"loss": loss.item()}

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
        return {"loss": avg_loss, "epoch": self.epoch}

    def evaluate(self, dataloader):
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch in dataloader:
                pixels = batch["pixels"].to(self.device)
                labels = batch.get("labels")
                if labels is not None:
                    labels = labels.to(self.device)
                outputs = self.model(pixels, labels=labels)
                total_loss += outputs["loss"].item()
                if labels is not None:
                    preds = outputs["logits"].argmax(dim=-1)
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)
        avg_loss = total_loss / max(len(dataloader), 1)
        accuracy = correct / max(total, 1)
        logger.info("Evaluation complete, loss: %.4f, accuracy: %.4f", avg_loss, accuracy)
        return {"loss": avg_loss, "accuracy": accuracy, "epoch": self.epoch}
