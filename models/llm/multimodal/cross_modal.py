from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiModalEmbedder(nn.Module):
    def __init__(
        self,
        vision_hidden_size: int = 768,
        text_hidden_size: int = 768,
        projection_dim: int = 512,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.vision_proj = nn.Linear(vision_hidden_size, projection_dim, bias=False, device=device, dtype=dtype)
        self.text_proj = nn.Linear(text_hidden_size, projection_dim, bias=False, device=device, dtype=dtype)
        self.logit_scale = nn.Parameter(torch.ones([]) * torch.log(torch.tensor(1.0 / 0.07)))

    def forward(
        self,
        vision_embeds: torch.Tensor,
        text_embeds: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        vision_projected = self.vision_proj(vision_embeds[:, 0, :])
        text_projected = self.text_proj(text_embeds[:, 0, :])
        return vision_projected, text_projected

    def encode_image(self, vision_embeds: torch.Tensor) -> torch.Tensor:
        embeds = self.vision_proj(vision_embeds[:, 0, :])
        return embeds / embeds.norm(dim=-1, keepdim=True)

    def encode_text(self, text_embeds: torch.Tensor) -> torch.Tensor:
        embeds = self.text_proj(text_embeds[:, 0, :])
        return embeds / embeds.norm(dim=-1, keepdim=True)

    def compute_similarity(self, vision_embeds: torch.Tensor, text_embeds: torch.Tensor) -> torch.Tensor:
        image_embeds = self.encode_image(vision_embeds)
        text_embeds_norm = self.encode_text(text_embeds)
        return self.logit_scale.exp() * image_embeds @ text_embeds_norm.t()


class SimilaritySearch:
    def __init__(self, embedder: MultiModalEmbedder, device: str = "cpu"):
        self.embedder = embedder
        self.device = device
        self.index: torch.Tensor | None = None
        self.metadata: list[dict] = []

    def build_index(self, vision_embeds_list: list[torch.Tensor], metadata: list[dict]) -> None:
        embeddings = []
        for vision_embeds in vision_embeds_list:
            emb = self.embedder.encode_image(vision_embeds.to(self.device))
            embeddings.append(emb)
        self.index = torch.cat(embeddings, dim=0) if embeddings else torch.empty(0)
        self.metadata = metadata

    def search(self, query_embeds: torch.Tensor, top_k: int = 5) -> list[dict]:
        if self.index is None or self.index.size(0) == 0:
            return []
        query_embeds = self.embedder.encode_text(query_embeds.to(self.device))
        scores = (self.index @ query_embeds.t()).squeeze(-1)
        top_scores, top_indices = torch.topk(scores, k=min(top_k, scores.size(0)))
        return [
            {"score": float(score), "index": int(idx), "metadata": self.metadata[int(idx)]}
            for score, idx in zip(top_scores.tolist(), top_indices.tolist())
        ]


class RetrievalAugmentedGenerator(nn.Module):
    def __init__(
        self,
        hidden_size: int = 768,
        num_layers: int = 4,
        num_attention_heads: int = 12,
        max_position_embeddings: int = 2048,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedder = MultiModalEmbedder(
            vision_hidden_size=hidden_size,
            text_hidden_size=hidden_size,
            projection_dim=hidden_size,
            device=device,
            dtype=dtype,
        )
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
        self.lm_head = nn.Linear(hidden_size, 32000, bias=False, device=device, dtype=dtype)
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)

    def forward(
        self,
        query_embeds: torch.Tensor,
        context_embeds: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T = input_ids.shape
        query = self.embedder.encode_text(query_embeds).unsqueeze(1)
        context = self.embedder.encode_image(context_embeds).unsqueeze(1)
        memory = torch.cat([query, context], dim=1)
        tgt = torch.cat([query.expand(-1, T, -1), self.embedder.text_proj.weight[input_ids]], dim=1)
        tgt = tgt[:, :T, :] + self.pos_embed[:, :T, :]
        tgt_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        tgt_mask = torch.triu(torch.ones(T, T, device=tgt.device, dtype=torch.bool), diagonal=1)
        out = self.decoder(tgt, memory, tgt_mask=tgt_mask, tgt_key_padding_mask=tgt_key_padding_mask)
        return self.lm_head(out)

    @torch.no_grad()
    def generate_with_retrieval(
        self,
        query_embeds: torch.Tensor,
        context_embeds: torch.Tensor,
        max_new_tokens: int = 128,
        temperature: float = 1.0,
    ) -> torch.Tensor:
        generated = torch.tensor([[1]], device=query_embeds.device, dtype=torch.long)
        for _ in range(max_new_tokens):
            logits = self.forward(query_embeds, context_embeds, generated)
            next_logits = logits[:, -1, :] / temperature
            probs = torch.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated = torch.cat([generated, next_token], dim=1)
            if next_token.item() == 2:
                break
        return generated
