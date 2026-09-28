from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn


class TextEncoder(nn.Module):
    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 192,
        num_layers: int = 6,
        num_attention_heads: int = 2,
        max_position_embeddings: int = 2048,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.pos_embed = nn.Parameter(
            torch.zeros(1, max_position_embeddings, hidden_size, device=device, dtype=dtype)
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_attention_heads,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.proj_mu = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self.proj_logvar = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None):
        B, T = input_ids.shape
        x = self.embedding(input_ids) + self.pos_embed[:, :T, :]
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        x = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        mu = self.proj_mu(x)
        logvar = self.proj_logvar(x)
        std = torch.exp(0.5 * logvar)
        z = mu + std * torch.randn_like(std)
        return z, mu, logvar


class Decoder(nn.Module):
    def __init__(
        self,
        hidden_size: int = 192,
        upsample_ratios: tuple[int, ...] = (8, 8, 2, 2),
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.input_proj = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self.upsample_layers = nn.ModuleList()
        current_dim = hidden_size
        for ratio in upsample_ratios:
            self.upsample_layers.append(
                nn.Sequential(
                    nn.ConvTranspose1d(
                        current_dim, current_dim // 2, kernel_size=ratio * 2,
                        stride=ratio, padding=ratio // 2, device=device, dtype=dtype,
                    ),
                    nn.ReLU(),
                )
            )
            current_dim //= 2
        self.output_proj = nn.Conv1d(current_dim, 1, kernel_size=7, padding=3, device=device, dtype=dtype)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(z).transpose(1, 2)
        for layer in self.upsample_layers:
            x = layer(x)
        return self.output_proj(x).squeeze(1)


class DurationPredictor(nn.Module):
    def __init__(self, hidden_size: int = 192, device=None, dtype=None):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size // 2, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1, device=device, dtype=dtype),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


class SpeechSynthesizer(nn.Module):
    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 192,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.text_encoder = TextEncoder(
            vocab_size=vocab_size, hidden_size=hidden_size, device=device, dtype=dtype,
        )
        self.decoder = Decoder(hidden_size=hidden_size, device=device, dtype=dtype)
        self.duration_predictor = DurationPredictor(hidden_size=hidden_size, device=device, dtype=dtype)
        self.flow = nn.Sequential(
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.Tanh(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z, mu, logvar = self.text_encoder(input_ids, attention_mask=attention_mask)
        z = self.flow(z)
        wav = self.decoder(z)
        log_durations = self.duration_predictor(z)
        return wav, mu, logvar

    @torch.no_grad()
    def synthesize(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        z, _, _ = self.text_encoder(input_ids, attention_mask=attention_mask)
        z = self.flow(z)
        return self.decoder(z)
