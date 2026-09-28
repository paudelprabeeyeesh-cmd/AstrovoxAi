from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


class FrameSampler(nn.Module):
    def __init__(self, num_frames: int = 8, hidden_size: int = 768, device=None, dtype=None):
        super().__init__()
        self.num_frames = num_frames
        self.frame_query = nn.Parameter(torch.zeros(1, num_frames, hidden_size, device=device, dtype=dtype))
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden_size,
            nhead=8,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=2)
        nn.init.normal_(self.frame_query, mean=0.0, std=0.02)

    def forward(self, frame_embeds: torch.Tensor) -> torch.Tensor:
        B = frame_embeds.size(0)
        queries = self.frame_query.expand(B, -1, -1)
        return self.decoder(queries, frame_embeds)


class TemporalModeling(nn.Module):
    def __init__(self, hidden_size: int = 768, num_layers: int = 4, device=None, dtype=None):
        super().__init__()
        self.pos_embed = nn.Parameter(
            torch.zeros(1, 256, hidden_size, device=device, dtype=dtype)
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=8,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        T = x.size(1)
        x = x + self.pos_embed[:, :T, :]
        return self.encoder(x)


class VideoEncoder(nn.Module):
    def __init__(
        self,
        num_frames: int = 8,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_attention_heads: int = 12,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.frame_sampler = FrameSampler(
            num_frames=num_frames,
            hidden_size=hidden_size,
            device=device,
            dtype=dtype,
        )
        self.temporal_model = TemporalModeling(
            hidden_size=hidden_size,
            num_layers=num_layers,
            device=device,
            dtype=dtype,
        )
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)

    def forward(self, frame_embeds: torch.Tensor) -> torch.Tensor:
        sampled = self.frame_sampler(frame_embeds)
        temporal = self.temporal_model(sampled)
        return self.ln(temporal)

    def get_video_embedding(self, frame_embeds: torch.Tensor) -> torch.Tensor:
        return self.forward(frame_embeds).mean(dim=1)


def sample_frames_uniform(total_frames: int, num_samples: int) -> list[int]:
    if total_frames <= num_samples:
        return list(range(total_frames))
    return [int(i * total_frames / num_samples) for i in range(num_samples)]


def sample_frames_adaptive(
    frame_scores: torch.Tensor,
    num_samples: int,
) -> list[int]:
    scores = frame_scores.squeeze()
    if scores.numel() <= num_samples:
        return list(range(scores.numel()))
    _, indices = torch.topk(scores, k=num_samples)
    return sorted(indices.tolist())
