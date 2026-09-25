"""
Embeddings API with batch processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

import torch
import torch.nn as nn
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel(nn.Module):
    """Simple embedding model for text."""

    def __init__(self, vocab_size: int = 32000, embed_dim: int = 384, max_seq_len: int = 512):
        super().__init__()
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.max_seq_len = max_seq_len
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.pos_embed = nn.Embedding(max_seq_len, embed_dim)
        self.norm = nn.LayerNorm(embed_dim)
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, input_ids: torch.Tensor, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        bsz, seq_len = input_ids.shape
        positions = torch.arange(seq_len, device=input_ids.device).unsqueeze(0).expand(bsz, -1)
        x = self.token_embed(input_ids) + self.pos_embed(positions)
        x = self.norm(x)
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).expand_as(x)
            x = x * mask
        x = x.transpose(1, 2)
        pooled = x.mean(dim=-1)
        return nn.functional.normalize(pooled, p=2, dim=-1)


class EmbeddingEngine:
    """High-level embedding engine with batch processing."""

    def __init__(self, model: Optional[EmbeddingModel] = None, batch_size: int = 32):
        self.model = model or EmbeddingModel()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        self.model.eval()
        self.batch_size = batch_size

    @torch.no_grad()
    def embed_texts(self, texts: List[str], tokenizer=None) -> np.ndarray:
        """Embed a batch of texts."""
        if tokenizer is None:
            from app.core.tokenizer import BPETokenizer
            tokenizer = BPETokenizer()
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            max_len = min(max(len(tokenizer.encode(t)) for t in batch), self.model.max_seq_len)
            input_ids = []
            masks = []
            for text in batch:
                ids = tokenizer.encode(text, add_bos=True, add_eos=True)[:max_len]
                padded = ids + [0] * (max_len - len(ids))
                mask = [1] * len(ids) + [0] * (max_len - len(ids))
                input_ids.append(padded)
                masks.append(mask)
            input_tensor = torch.tensor(input_ids, device=self.device)
            mask_tensor = torch.tensor(masks, device=self.device)
            embeddings = self.model(input_tensor, attention_mask=mask_tensor)
            all_embeddings.append(embeddings.cpu().numpy())
        return np.vstack(all_embeddings)

    def embed_query(self, text: str, tokenizer=None) -> np.ndarray:
        """Embed a single query text."""
        result = self.embed_texts([text], tokenizer=tokenizer)
        return result[0]

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two embeddings."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
