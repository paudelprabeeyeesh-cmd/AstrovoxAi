from __future__ import annotations

import math
from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. VITS-style TTS Components
# ---------------------------------------------------------------------------


class TextEncoder(nn.Module):
    """Text encoder producing latent representations for TTS."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 192,
        num_layers: int = 6,
        num_attention_heads: int = 2,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.pos_embed = nn.Parameter(
            torch.zeros(1, 2048, hidden_size, device=device, dtype=dtype)
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

    def _reset_parameters(self):
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
    """VITS-style decoder with upsampling and waveform generation."""

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
    """Predict phoneme durations for alignment."""

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


class TTSModel(nn.Module):
    """VITS-style text-to-speech model with duration prediction."""

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


# ---------------------------------------------------------------------------
# 2. Voice Cloning
# ---------------------------------------------------------------------------


class SpeakerEncoder(nn.Module):
    """Speaker encoder for voice cloning using reference audio."""

    def __init__(
        self,
        mel_channels: int = 80,
        hidden_size: int = 768,
        output_dim: int = 256,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.conv_layers = nn.Sequential(
            nn.Conv1d(mel_channels, hidden_size // 4, kernel_size=5, padding=2, device=device, dtype=dtype),
            nn.BatchNorm1d(hidden_size // 4, device=device, dtype=dtype if dtype != torch.float16 else torch.float32),
            nn.ReLU(),
            nn.Conv1d(hidden_size // 4, hidden_size // 2, kernel_size=5, padding=2, device=device, dtype=dtype),
            nn.BatchNorm1d(hidden_size // 2, device=device, dtype=dtype if dtype != torch.float16 else torch.float32),
            nn.ReLU(),
            nn.Conv1d(hidden_size // 2, hidden_size, kernel_size=5, padding=2, device=device, dtype=dtype),
            nn.BatchNorm1d(hidden_size, device=device, dtype=dtype if dtype != torch.float16 else torch.float32),
            nn.ReLU(),
        )
        self.lstm = nn.LSTM(
            hidden_size, hidden_size // 2, num_layers=3, batch_first=True, bidirectional=True,
            device=device, dtype=dtype,
        )
        self.fc = nn.Linear(hidden_size, output_dim, device=device, dtype=dtype)

    def forward(self, mel: torch.Tensor) -> torch.Tensor:
        x = self.conv_layers(mel).transpose(1, 2)
        _, (h_n, _) = self.lstm(x)
        emb = torch.cat([h_n[-2], h_n[-1]], dim=-1)
        return self.fc(emb)


class VoiceCloneTTS(nn.Module):
    """Voice cloning TTS with speaker conditioning."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 192,
        speaker_embed_dim: int = 256,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.speaker_encoder = SpeakerEncoder(
            mel_channels=80, hidden_size=hidden_size * 2, output_dim=speaker_embed_dim,
            device=device, dtype=dtype,
        )
        self.text_encoder = TextEncoder(
            vocab_size=vocab_size, hidden_size=hidden_size, device=device, dtype=dtype,
        )
        self.speaker_proj = nn.Linear(speaker_embed_dim, hidden_size, device=device, dtype=dtype)
        self.decoder = Decoder(hidden_size=hidden_size, device=device, dtype=dtype)
        self.duration_predictor = DurationPredictor(hidden_size=hidden_size, device=device, dtype=dtype)

    def forward(
        self,
        input_ids: torch.Tensor,
        reference_mel: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        z, mu, logvar = self.text_encoder(input_ids, attention_mask=attention_mask)
        speaker_emb = self.speaker_encoder(reference_mel)
        spk_cond = self.speaker_proj(speaker_emb).unsqueeze(1)
        z = z + spk_cond
        wav = self.decoder(z)
        log_durations = self.duration_predictor(z)
        return wav, log_durations

    @torch.no_grad()
    def clone_voice(
        self,
        input_ids: torch.Tensor,
        reference_mel: torch.Tensor,
        max_new_tokens: int = 1000,
    ) -> torch.Tensor:
        z, _, _ = self.text_encoder(input_ids)
        speaker_emb = self.speaker_encoder(reference_mel)
        z = z + self.speaker_proj(speaker_emb).unsqueeze(1)
        wav = self.decoder(z)
        return wav
