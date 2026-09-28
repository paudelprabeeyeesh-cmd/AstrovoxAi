from __future__ import annotations

from typing import Literal

import torch
import torch.nn as nn


class DocumentParser(nn.Module):
    def __init__(
        self,
        hidden_size: int = 768,
        num_layers: int = 6,
        num_attention_heads: int = 12,
        vocab_size: int = 32000,
        max_position_embeddings: int = 2048,
        device=None,
        dtype=None,
    ):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_attention_heads,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False, device=device, dtype=dtype)

    def forward(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        out = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        return self.lm_head(out)

    @torch.no_grad()
    def parse(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        logits = self.forward(x, attention_mask=attention_mask)
        return torch.argmax(logits, dim=-1)


class LayoutAnalyzer(nn.Module):
    def __init__(
        self,
        hidden_size: int = 768,
        num_classes: int = 10,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=8,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.encoder = nn.TransformerEncoder(self.encoder_layer, num_layers=4)
        self.classifier = nn.Linear(hidden_size, num_classes, device=device, dtype=dtype)
        self.bbox_regressor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, 4, device=device, dtype=dtype),
        )

    def forward(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        src_key_padding_mask = (attention_mask == 0) if attention_mask is not None else None
        out = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        logits = self.classifier(out)
        boxes = self.bbox_regressor(out).sigmoid()
        return logits, boxes

    def predict_layout(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> dict:
        logits, boxes = self.forward(x, attention_mask=attention_mask)
        pred_classes = torch.argmax(logits, dim=-1)
        return {
            "layout_classes": pred_classes,
            "bounding_boxes": boxes,
            "logits": logits,
        }


class TableExtractor(nn.Module):
    def __init__(
        self,
        hidden_size: int = 768,
        max_cells: int = 256,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.max_cells = max_cells
        self.cell_query = nn.Parameter(torch.zeros(1, max_cells, hidden_size, device=device, dtype=dtype))
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden_size,
            nhead=8,
            batch_first=True,
            device=device,
            dtype=dtype,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=4)
        self.cell_content_head = nn.Linear(hidden_size, 1, device=device, dtype=dtype)
        self.cell_bbox_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 4, device=device, dtype=dtype),
        )
        nn.init.normal_(self.cell_query, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        B = x.size(0)
        queries = self.cell_query.expand(B, -1, -1)
        decoded = self.decoder(queries, x)
        content_logits = self.cell_content_head(decoded).squeeze(-1)
        cell_boxes = self.cell_bbox_head(decoded).sigmoid()
        return content_logits, cell_boxes

    def extract_table(self, x: torch.Tensor) -> dict:
        content_logits, cell_boxes = self.forward(x)
        return {
            "cell_logits": content_logits,
            "cell_boxes": cell_boxes,
            "max_cells": self.max_cells,
        }
