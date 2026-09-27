import torch
import torch.nn as nn
import torch.nn.functional as F
from .transformer import TransformerBlock, OutputLayer, LayerNorm


class LLM(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.vocab_size = config["vocab_size"]
        self.hidden_size = config["hidden_size"]
        self.num_hidden_layers = config["num_hidden_layers"]
        self.num_attention_heads = config["num_attention_heads"]
        self.intermediate_size = config["intermediate_size"]
        self.max_position_embeddings = config.get("max_position_embeddings", 1024)
        self.dropout = config.get("dropout", 0.0)
        self.layer_norm_epsilon = config.get("layer_norm_epsilon", 1e-5)

        self.token_embedding = nn.Embedding(self.vocab_size, self.hidden_size)
        self.position_embedding = nn.Embedding(self.max_position_embeddings, self.hidden_size)
        self.embed_dropout = nn.Dropout(self.dropout)

        self.blocks = nn.ModuleList([
            TransformerBlock(
                self.hidden_size,
                self.num_attention_heads,
                self.intermediate_size,
                self.dropout,
                self.max_position_embeddings,
                self.layer_norm_epsilon,
            )
            for _ in range(self.num_hidden_layers)
        ])

        self.ln_f = LayerNorm(self.hidden_size, eps=self.layer_norm_epsilon)
        self.lm_head = nn.Linear(self.hidden_size, self.vocab_size, bias=False)
        self.token_embedding.weight = self.lm_head.weight

        self.apply(self._init_weights)

    @classmethod
    def from_config(cls, config):
        return cls(config)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, input_ids, labels=None, use_gradient_checkpointing=False):
        B, T = input_ids.size()
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x = self.token_embedding(input_ids) + self.position_embedding(pos)
        x = self.embed_dropout(x)

        for block in self.blocks:
            if use_gradient_checkpointing and self.training:
                x = torch.utils.checkpoint.checkpoint(block, x, use_reentrant=False)
            else:
                x = block(x)

        x = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)
        return {"logits": logits, "loss": loss}

    def get_num_params(self, trainable_only=True):
        try:
            if trainable_only:
                return sum(p.numel() for p in self.parameters() if p.requires_grad)
            return sum(p.numel() for p in self.parameters())
        except Exception:
            return 0
