from __future__ import annotations

import math
from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


class PatchEmbedding(nn.Module):
    def __init__(
        self,
        image_size: int = 224,
        patch_size: int = 16,
        num_channels: int = 3,
        hidden_size: int = 768,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.image_size = image_size
        self.patch_size = patch_size
        self.num_patches = (image_size // patch_size) ** 2
        self.proj = nn.Conv2d(
            num_channels,
            hidden_size,
            kernel_size=patch_size,
            stride=patch_size,
            bias=True,
            device=device,
            dtype=dtype,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)
        x = x.flatten(2).transpose(1, 2)
        return x


class VisionEncoder(nn.Module):
    def __init__(
        self,
        image_size: int = 224,
        patch_size: int = 16,
        num_channels: int = 3,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_attention_heads: int = 12,
        mlp_ratio: float = 4.0,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.patch_embed = PatchEmbedding(
            image_size=image_size,
            patch_size=patch_size,
            num_channels=num_channels,
            hidden_size=hidden_size,
            device=device,
            dtype=dtype,
        )
        num_patches = self.patch_embed.num_patches
        self.cls_token = nn.Parameter(torch.zeros(1, 1, hidden_size, device=device, dtype=dtype))
        self.pos_embed = nn.Parameter(
            torch.zeros(1, num_patches + 1, hidden_size, device=device, dtype=dtype)
        )
        self.pos_dropout = nn.Dropout(dropout)
        self.blocks = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=hidden_size,
                    nhead=num_attention_heads,
                    dim_feedforward=int(hidden_size * mlp_ratio),
                    dropout=dropout,
                    batch_first=True,
                    device=device,
                    dtype=dtype,
                )
                for _ in range(num_layers)
            ]
        )
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)
        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.patch_embed(x)
        B = x.size(0)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        x = x + self.pos_embed
        x = self.pos_dropout(x)
        for block in self.blocks:
            x = block(x)
        x = self.ln(x)
        return x

    def get_image_embedding(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward(x)[:, 0, :]

    def get_patch_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        return self.forward(x)[:, 1:, :]


def preprocess_image(
    x: torch.Tensor,
    mean: tuple[float, float, float] = (0.485, 0.456, 0.406),
    std: tuple[float, float, float] = (0.229, 0.224, 0.225),
) -> torch.Tensor:
    tensor = x.float() / 255.0 if x.dtype == torch.uint8 else x.float()
    mean_tensor = torch.tensor(mean, device=tensor.device).view(1, 3, 1, 1)
    std_tensor = torch.tensor(std, device=tensor.device).view(1, 3, 1, 1)
    return (tensor - mean_tensor) / std_tensor


def resize_image(x: torch.Tensor, size: int) -> torch.Tensor:
    return F.interpolate(x, size=(size, size), mode="bilinear", align_corners=False)


class VisionLLMIntegration(nn.Module):
    def __init__(
        self,
        vision_hidden_size: int = 768,
        llm_hidden_size: int = 768,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.proj = nn.Linear(vision_hidden_size, llm_hidden_size, bias=False, device=device, dtype=dtype)

    def forward(self, vision_embeds: torch.Tensor) -> torch.Tensor:
        return self.proj(vision_embeds)
