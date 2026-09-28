from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# 1. Speech Encoder (Whisper-style)
# ---------------------------------------------------------------------------


class SpeechEncoder(nn.Module):
    """Whisper-style convolutional + transformer speech encoder."""

    def __init__(
        self,
        num_mel_bins: int = 80,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_attention_heads: int = 12,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.conv1 = nn.Conv1d(
            num_mel_bins, hidden_size, kernel_size=3, padding=1, device=device, dtype=dtype
        )
        self.conv2 = nn.Conv1d(
            hidden_size, hidden_size, kernel_size=3, stride=2, padding=1, device=device, dtype=dtype
        )
        self.gelu = nn.GELU()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_attention_heads,
            dropout=dropout,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

    def forward(self, mel_spectrogram: torch.Tensor) -> torch.Tensor:
        x = self.gelu(self.conv1(mel_spectrogram))
        x = self.gelu(self.conv2(x))
        x = x.transpose(1, 2)
        return self.encoder(x)


# ---------------------------------------------------------------------------
# 2. Speech Decoder
# ---------------------------------------------------------------------------


class SpeechDecoder(nn.Module):
    """Autoregressive decoder for speech-to-text generation."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 6,
        num_attention_heads: int = 12,
        max_position_embeddings: int = 1024,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.pos_embed = nn.Parameter(
            torch.zeros(1, max_position_embeddings, hidden_size, device=device, dtype=dtype)
        )
        self.dropout = nn.Dropout(0.1)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden_size,
            nhead=num_attention_heads,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=num_layers)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        encoder_hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T = input_ids.shape
        x = self.token_embedding(input_ids) + self.pos_embed[:, :T, :]
        x = self.dropout(x)
        tgt_mask = torch.triu(torch.ones(T, T, device=x.device, dtype=torch.bool), diagonal=1)
        tgt_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        x = self.decoder(
            x,
            encoder_hidden_states,
            tgt_mask=tgt_mask,
            tgt_key_padding_mask=tgt_key_padding_mask,
        )
        return self.lm_head(x)


# ---------------------------------------------------------------------------
# 3. Speech Recognition Model
# ---------------------------------------------------------------------------


class SpeechRecognitionModel(nn.Module):
    """End-to-end speech recognition model (speech-to-text)."""

    def __init__(
        self,
        vocab_size: int = 32000,
        num_mel_bins: int = 80,
        hidden_size: int = 768,
        encoder_num_layers: int = 12,
        decoder_num_layers: int = 6,
        num_attention_heads: int = 12,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.encoder = SpeechEncoder(
            num_mel_bins=num_mel_bins,
            hidden_size=hidden_size,
            num_layers=encoder_num_layers,
            num_attention_heads=num_attention_heads,
            device=device,
            dtype=dtype,
        )
        self.decoder = SpeechDecoder(
            vocab_size=vocab_size,
            hidden_size=hidden_size,
            num_layers=decoder_num_layers,
            num_attention_heads=num_attention_heads,
            device=device,
            dtype=dtype,
        )

    def forward(
        self,
        mel_spectrogram: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        encoder_out = self.encoder(mel_spectrogram)
        return self.decoder(input_ids, encoder_out, attention_mask=attention_mask)

    @torch.no_grad()
    def generate(
        self,
        mel_spectrogram: torch.Tensor,
        max_new_tokens: int = 256,
        temperature: float = 1.0,
        top_k: int | None = None,
    ) -> torch.Tensor:
        encoder_out = self.encoder(mel_spectrogram.unsqueeze(0))
        generated = torch.tensor([[0]], device=mel_spectrogram.device, dtype=torch.long)
        for _ in range(max_new_tokens):
            logits = self.decoder(generated, encoder_out)
            next_logits = logits[:, -1, :] / temperature
            if top_k is not None:
                top_k = min(top_k, next_logits.size(-1))
                indices_to_remove = next_logits < torch.topk(next_logits, top_k)[0][..., -1, None]
                next_logits = next_logits.masked_fill(indices_to_remove, float("-inf"))
            probs = F.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated = torch.cat([generated, next_token], dim=1)
            if next_token.item() == 1:
                break
        return generated
