from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn


class ImageCaptioner(nn.Module):
    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 6,
        num_attention_heads: int = 12,
        max_position_embeddings: int = 128,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.vision_proj = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self.token_embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.pos_embed = nn.Parameter(
            torch.zeros(1, max_position_embeddings, hidden_size, device=device, dtype=dtype)
        )
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

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(
        self,
        vision_embeds: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T = input_ids.shape
        memory = self.vision_proj(vision_embeds)
        tgt = self.token_embedding(input_ids) + self.pos_embed[:, :T, :]
        tgt_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        tgt_mask = torch.triu(torch.ones(T, T, device=tgt.device, dtype=torch.bool), diagonal=1)
        out = self.decoder(
            tgt,
            memory,
            tgt_mask=tgt_mask,
            tgt_key_padding_mask=tgt_key_padding_mask,
        )
        return self.lm_head(out)

    @torch.no_grad()
    def caption(self, vision_embeds: torch.Tensor, max_new_tokens: int = 64, temperature: float = 1.0) -> torch.Tensor:
        generated = torch.tensor([[1]], device=vision_embeds.device, dtype=torch.long)
        for _ in range(max_new_tokens):
            logits = self.forward(vision_embeds, generated)
            next_logits = logits[:, -1, :] / temperature
            probs = torch.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated = torch.cat([generated, next_token], dim=1)
            if next_token.item() == 2:
                break
        return generated


class VisualQuestionAnswerer(nn.Module):
    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 6,
        num_attention_heads: int = 12,
        max_position_embeddings: int = 256,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.vision_proj = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)
        self.token_embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.pos_embed = nn.Parameter(
            torch.zeros(1, max_position_embeddings, hidden_size, device=device, dtype=dtype)
        )
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

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(
        self,
        vision_embeds: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T = input_ids.shape
        memory = self.vision_proj(vision_embeds)
        tgt = self.token_embedding(input_ids) + self.pos_embed[:, :T, :]
        tgt_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        tgt_mask = torch.triu(torch.ones(T, T, device=tgt.device, dtype=torch.bool), diagonal=1)
        out = self.decoder(
            tgt,
            memory,
            tgt_mask=tgt_mask,
            tgt_key_padding_mask=tgt_key_padding_mask,
        )
        return self.lm_head(out)

    @torch.no_grad()
    def answer(
        self,
        vision_embeds: torch.Tensor,
        question_ids: torch.Tensor,
        max_new_tokens: int = 32,
        temperature: float = 1.0,
    ) -> torch.Tensor:
        generated = torch.cat([question_ids, torch.tensor([[1]], device=question_ids.device)], dim=1)
        for _ in range(max_new_tokens):
            logits = self.forward(vision_embeds, generated)
            next_logits = logits[:, -1, :] / temperature
            probs = torch.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated = torch.cat([generated, next_token], dim=1)
            if next_token.item() == 2:
                break
        return generated


class ObjectDetector(nn.Module):
    def __init__(
        self,
        hidden_size: int = 768,
        num_queries: int = 100,
        num_classes: int = 80,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.num_queries = num_queries
        self.query_embed = nn.Parameter(torch.zeros(1, num_queries, hidden_size, device=device, dtype=dtype))
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden_size,
            nhead=8,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=6)
        self.class_embed = nn.Linear(hidden_size, num_classes + 1, device=device, dtype=dtype)
        self.bbox_embed = nn.Sequential(
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, 4, device=device, dtype=dtype),
        )
        nn.init.normal_(self.query_embed, mean=0.0, std=0.02)

    def forward(self, vision_embeds: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        B = vision_embeds.size(0)
        queries = self.query_embed.expand(B, -1, -1)
        decoded = self.decoder(queries, vision_embeds)
        pred_logits = self.class_embed(decoded)
        pred_boxes = self.bbox_embed(decoded).sigmoid()
        return pred_logits, pred_boxes
