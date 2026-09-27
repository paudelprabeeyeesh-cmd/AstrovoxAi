from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 1. Vision Transformer (ViT)
# ---------------------------------------------------------------------------


class VisionTransformerEncoder(nn.Module):
    """Vision Transformer encoder with patch embedding."""

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
        self.patch_embed = nn.Conv2d(
            num_channels,
            hidden_size,
            kernel_size=patch_size,
            stride=patch_size,
            bias=True,
            device=device,
            dtype=dtype,
        )
        num_patches = (image_size // patch_size) ** 2
        self.pos_embed = nn.Parameter(
            torch.zeros(1, num_patches + 1, hidden_size, device=device, dtype=dtype)
        )
        self.cls_token = nn.Parameter(torch.zeros(1, 1, hidden_size, device=device, dtype=dtype))
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

    def _reset_parameters(self):
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)
        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B = x.size(0)
        x = self.patch_embed(x).flatten(2).transpose(1, 2)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        x = x + self.pos_embed
        x = self.pos_dropout(x)
        for block in self.blocks:
            x = block(x)
        x = self.ln(x)
        return x


# ---------------------------------------------------------------------------
# 2. CLIP-style Text Encoder
# ---------------------------------------------------------------------------


class CLIPTextEncoder(nn.Module):
    """CLIP-style text encoder with causal attention mask."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_attention_heads: int = 12,
        max_position_embeddings: int = 77,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.pos_embed = nn.Parameter(
            torch.zeros(1, max_position_embeddings, hidden_size, device=device, dtype=dtype)
        )
        self.blocks = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=hidden_size,
                    nhead=num_attention_heads,
                    batch_first=True,
                    device=device,
                    dtype=dtype,
                )
                for _ in range(num_layers)
            ]
        )
        self.ln = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        B, T = input_ids.shape
        x = self.token_embedding(input_ids) + self.pos_embed[:, :T, :]
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        for block in self.blocks:
            x = block(x, src_key_padding_mask=src_key_padding_mask)
        x = self.ln(x)
        return x


# ---------------------------------------------------------------------------
# 3. Cross-Modal Attention
# ---------------------------------------------------------------------------


class CrossModalAttentionBlock(nn.Module):
    """Bidirectional cross-attention between vision and text modalities."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_heads: int = 12,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_heads != 0:
            raise ValueError("hidden_size must be divisible by num_heads")
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)
        self.ln_q = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.ln_kv = nn.LayerNorm(hidden_size, device=device, dtype=dtype)

    def forward(
        self,
        query_states: torch.Tensor,
        key_value_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T, C = query_states.shape
        q = self.q_proj(self.ln_q(query_states)).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(self.ln_kv(key_value_states)).view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(self.ln_kv(key_value_states)).view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        if attention_mask is not None:
            attn = attn + attention_mask
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(query_states.dtype)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


# ---------------------------------------------------------------------------
# 4. Image-Text Alignment (CLIP-style)
# ---------------------------------------------------------------------------


class CLIPModel(nn.Module):
    """CLIP-style image-text alignment model."""

    def __init__(
        self,
        vocab_size: int = 32000,
        image_size: int = 224,
        patch_size: int = 16,
        num_channels: int = 3,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_attention_heads: int = 12,
        max_position_embeddings: int = 77,
        projection_dim: int = 512,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.vision_encoder = VisionTransformerEncoder(
            image_size=image_size,
            patch_size=patch_size,
            num_channels=num_channels,
            hidden_size=hidden_size,
            num_layers=num_layers,
            num_attention_heads=num_attention_heads,
            device=device,
            dtype=dtype,
        )
        self.text_encoder = CLIPTextEncoder(
            vocab_size=vocab_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            num_attention_heads=num_attention_heads,
            max_position_embeddings=max_position_embeddings,
            device=device,
            dtype=dtype,
        )
        self.vision_proj = nn.Linear(hidden_size, projection_dim, bias=False, device=device, dtype=dtype)
        self.text_proj = nn.Linear(hidden_size, projection_dim, bias=False, device=device, dtype=dtype)
        self.logit_scale = nn.Parameter(torch.ones([]) * math.log(1.0 / 0.07))

    def encode_image(self, images: torch.Tensor) -> torch.Tensor:
        image_embeds = self.vision_encoder(images)
        return self.vision_proj(image_embeds[:, 0, :])

    def encode_text(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        text_embeds = self.text_encoder(input_ids, attention_mask=attention_mask)
        return self.text_proj(text_embeds[:, 0, :])

    def forward(
        self,
        images: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        image_embeds = self.encode_image(images)
        text_embeds = self.encode_text(input_ids, attention_mask=attention_mask)
        image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
        text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)
        logit_scale = self.logit_scale.exp()
        logits_per_image = logit_scale * image_embeds @ text_embeds.t()
        logits_per_text = logits_per_image.t()
        return logits_per_image, logits_per_text


# ---------------------------------------------------------------------------
# 5. Multimodal Fusion
# ---------------------------------------------------------------------------


class MultimodalFusionBlock(nn.Module):
    """Fusion block combining vision and text representations."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_heads: int = 12,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.cross_attn_v2t = CrossModalAttentionBlock(
            hidden_size=hidden_size, num_heads=num_heads, dropout=dropout, device=device, dtype=dtype,
        )
        self.cross_attn_t2v = CrossModalAttentionBlock(
            hidden_size=hidden_size, num_heads=num_heads, dropout=dropout, device=device, dtype=dtype,
        )
        self.ln_v = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.ln_t = nn.LayerNorm(hidden_size, device=device, dtype=dtype)
        self.mlp = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size, bias=False, device=device, dtype=dtype),
            nn.SiLU(),
            nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        vision_embeds: torch.Tensor,
        text_embeds: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        v = self.cross_attn_v2t(vision_embeds, text_embeds, attention_mask)
        t = self.cross_attn_t2v(text_embeds, vision_embeds, attention_mask)
        fused = self.mlp(torch.cat([self.ln_v(v), self.ln_t(t)], dim=-1))
        return fused
