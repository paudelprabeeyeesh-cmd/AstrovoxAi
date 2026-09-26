"""
Cross-modal learning for vision-language models with contrastive learning.
"""

from __future__ import annotations

import logging
from typing import Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class VisionLanguageModel(nn.Module):
    def __init__(self, vision_encoder: nn.Module, text_encoder: nn.Module, proj_dim: int = 512):
        super().__init__()
        self.vision_encoder = vision_encoder
        self.text_encoder = text_encoder
        self.vision_proj = nn.Linear(vision_encoder.config.hidden_size, proj_dim)
        self.text_proj = nn.Linear(text_encoder.config.hidden_size, proj_dim)
        self.temperature = nn.Parameter(torch.tensor(0.07))

    def forward(self, images: torch.Tensor, text_ids: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        image_embeds = self.vision_encoder(images).last_hidden_state.mean(dim=1)
        text_embeds = self.text_encoder(text_ids).last_hidden_state.mean(dim=1)
        image_embeds = self.vision_proj(image_embeds)
        text_embeds = self.text_proj(text_embeds)
        return image_embeds, text_embeds

    def contrastive_loss(self, image_embeds: torch.Tensor, text_embeds: torch.Tensor) -> torch.Tensor:
        image_embeds = F.normalize(image_embeds, dim=-1)
        text_embeds = F.normalize(text_embeds, dim=-1)
        logits = torch.matmul(image_embeds, text_embeds.t()) / self.temperature
        labels = torch.arange(logits.size(0), device=logits.device)
        loss_i2t = F.cross_entropy(logits, labels)
        loss_t2i = F.cross_entropy(logits.t(), labels)
        return (loss_i2t + loss_t2i) / 2


class MultimodalFusion(nn.Module):
    def __init__(self, hidden_size: int, num_modalities: int = 2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_modalities = num_modalities
        self.fusion_layer = nn.Linear(hidden_size * num_modalities, hidden_size)
        self.gate = nn.Linear(hidden_size * num_modalities, num_modalities)

    def forward(self, *modality_embeddings: torch.Tensor) -> torch.Tensor:
        concat = torch.cat(modality_embeddings, dim=-1)
        gate_weights = F.softmax(self.gate(concat), dim=-1)
        weighted = torch.cat([gate_weights[:, i:i + 1] * modality_embeddings[i] for i in range(self.num_modalities)], dim=-1)
        return self.fusion_layer(weighted)
