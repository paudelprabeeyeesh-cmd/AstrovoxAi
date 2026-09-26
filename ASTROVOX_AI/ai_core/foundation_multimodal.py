import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging
import math
import os

from .transformers.transformer_from_scratch import TransformerConfig, TransformerFromScratch, TransformerBlock

logger = logging.getLogger(__name__)


@dataclass
class MultimodalConfig:
    text_vocab_size: int = 50257
    image_dim: int = 768
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    dropout: float = 0.1
    projection_dim: int = 256


class TextEncoder(nn.Module):
    def __init__(self, config: MultimodalConfig):
        super().__init__()
        self.config = config
        t_config = TransformerConfig(
            vocab_size=config.text_vocab_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            num_heads=config.num_heads,
            intermediate_size=config.hidden_size * 4,
            max_position_embeddings=512,
            dropout=config.dropout,
        )
        self.transformer = TransformerFromScratch(t_config)
        self.projection = nn.Linear(config.hidden_size, config.projection_dim)
        self.ln = nn.LayerNorm(config.projection_dim)

    def forward(self, input_ids):
        hidden = self.transformer(input_ids)
        cls_hidden = hidden[:, 0, :]
        projected = self.projection(cls_hidden)
        return self.ln(projected)


class ImageEncoder(nn.Module):
    def __init__(self, config: MultimodalConfig):
        super().__init__()
        self.config = config
        self.patch_embed = nn.Conv2d(3, config.hidden_size, kernel_size=16, stride=16)
        num_patches = (224 // 16) ** 2
        self.cls_token = nn.Parameter(torch.zeros(1, 1, config.hidden_size))
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, config.hidden_size))
        self.dropout = nn.Dropout(config.dropout)
        t_config = TransformerConfig(
            vocab_size=0,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            num_heads=config.num_heads,
            intermediate_size=config.hidden_size * 4,
            max_position_embeddings=num_patches + 1,
            dropout=config.dropout,
        )
        self.blocks = nn.ModuleList([TransformerBlock(t_config) for _ in range(config.num_layers)])
        self.ln_f = nn.LayerNorm(config.hidden_size)
        self.projection = nn.Linear(config.hidden_size, config.projection_dim)
        self.ln = nn.LayerNorm(config.projection_dim)

    def forward(self, pixels):
        x = self.patch_embed(pixels).flatten(2).transpose(1, 2)
        cls_tokens = self.cls_token.expand(pixels.size(0), -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        x = x + self.pos_embed[:, :x.size(1), :]
        x = self.dropout(x)
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        cls_hidden = x[:, 0, :]
        projected = self.projection(cls_hidden)
        return self.ln(projected)


class MultimodalModel(nn.Module):
    def __init__(self, config: Optional[MultimodalConfig] = None):
        super().__init__()
        self.config = config or MultimodalConfig()
        self.text_encoder = TextEncoder(self.config)
        self.image_encoder = ImageEncoder(self.config)
        self.logit_scale = nn.Parameter(torch.ones([]) * math.log(1 / 0.07))
        logger.info("Multimodal model initialized")

    def encode_text(self, text):
        return self.text_encoder(text)

    def encode_image(self, image):
        return self.image_encoder(image)

    def forward(self, text, image):
        text_emb = self.encode_text(text)
        image_emb = self.encode_image(image)
        return {"text_emb": text_emb, "image_emb": image_emb, "logit_scale": self.logit_scale}


class MultimodalTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        logger.info("MultimodalTrainer initialized")

    def contrastive_step(self, text_batch, image_batch):
        self.model.train()
        text = text_batch["input_ids"].to(self.device)
        image = image_batch["pixels"].to(self.device)
        outputs = self.model(text, image)
        text_emb = outputs["text_emb"]
        image_emb = outputs["image_emb"]
        logit_scale = outputs["logit_scale"].exp()
        logits = logit_scale * text_emb @ image_emb.t()
        labels = torch.arange(text.size(0), device=self.device)
        loss_i2t = F.cross_entropy(logits, labels)
        loss_t2i = F.cross_entropy(logits.t(), labels)
        loss = (loss_i2t + loss_t2i) / 2
        loss.backward()
        if self.grad_clip > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        self.optimizer.zero_grad()
        return {"loss": loss.item()}
