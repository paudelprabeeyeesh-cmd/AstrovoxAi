import torch
import torch.nn as nn
from .transformer import TransformerBlock, OutputLayer, RMSNorm


def _prepare_4d_attention_mask(attention_mask: torch.Tensor, dtype: torch.dtype, device: torch.device) -> torch.Tensor:
    if attention_mask is None:
        return None
    if attention_mask.dim() == 2:
        batch_size, seq_len = attention_mask.size()
        causal_mask = torch.triu(torch.ones(seq_len, seq_len, device=device, dtype=torch.bool), diagonal=1)
        expanded_mask = attention_mask.unsqueeze(1).unsqueeze(2)
        expanded_mask = expanded_mask.expand(batch_size, 1, seq_len, seq_len)
        combined = torch.masked_fill(torch.zeros(seq_len, seq_len, device=device, dtype=dtype), causal_mask, float("-inf"))
        combined = combined.unsqueeze(0).unsqueeze(0).expand(batch_size, 1, seq_len, seq_len)
        combined = combined + (~expanded_mask * torch.finfo(dtype).min)
        return combined.to(dtype)
    return attention_mask.to(dtype)


class LLM(nn.Module):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.vocab_size = int(config["vocab_size"])
        self.hidden_size = int(config["hidden_size"])
        self.num_hidden_layers = int(config["num_hidden_layers"])
        self.num_attention_heads = int(config["num_attention_heads"])
        self.intermediate_size = int(config["intermediate_size"])
        self.max_position_embeddings = int(config.get("max_position_embeddings", 2048))
        self.rms_norm_eps = float(config.get("rms_norm_eps", 1e-5))
        self.rope_theta = float(config.get("rope_theta", 10000.0))
        self.activation = config.get("activation", "swiglu")
        self.attention_bias = bool(config.get("attention_bias", False))
        self.mlp_bias = bool(config.get("mlp_bias", False))
        self.dropout = float(config.get("dropout", 0.0))
        self.tie_weights = bool(config.get("tie_weights", True))

        self.token_embedding = nn.Embedding(self.vocab_size, self.hidden_size)
        self.embed_dropout = nn.Dropout(self.dropout)

        self.blocks = nn.ModuleList([
            TransformerBlock(
                hidden_size=self.hidden_size,
                num_attention_heads=self.num_attention_heads,
                intermediate_size=self.intermediate_size,
                max_position_embeddings=self.max_position_embeddings,
                rope_theta=self.rope_theta,
                rms_norm_eps=self.rms_norm_eps,
                dropout=self.dropout,
                activation=self.activation,
                attention_bias=self.attention_bias,
                mlp_bias=self.mlp_bias,
            )
            for _ in range(self.num_hidden_layers)
        ])

        self.ln_f = RMSNorm(self.hidden_size, eps=self.rms_norm_eps)
        self.lm_head = OutputLayer(self.hidden_size, self.vocab_size, tie_weights=self.tie_weights)
        if self.tie_weights:
            self.token_embedding.weight = self.lm_head.lm_head.weight

        self.apply(self._init_weights)

    @classmethod
    def from_config(cls, config: dict):
        return cls(config)

    def _init_weights(self, module: nn.Module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, RMSNorm):
            nn.init.ones_(module.weight)

    def get_position_ids(self, seq_len: int, device: torch.device) -> torch.Tensor:
        return torch.arange(seq_len, device=device, dtype=torch.long).unsqueeze(0)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        use_gradient_checkpointing: bool = False,
    ) -> dict:
        B, T = input_ids.size()
        if attention_mask is not None and attention_mask.dim() == 2:
            attention_mask = _prepare_4d_attention_mask(attention_mask, input_ids.dtype, input_ids.device)

        x = self.token_embedding(input_ids)
        x = self.embed_dropout(x)

        position_ids = self.get_position_ids(T, input_ids.device)
        for block in self.blocks:
            x = block(x, position_ids=position_ids, attention_mask=attention_mask, use_gradient_checkpointing=use_gradient_checkpointing)

        x = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)
        return {"logits": logits, "loss": loss}

    def get_num_params(self, trainable_only: bool = True) -> int:
        try:
            if trainable_only:
                return sum(p.numel() for p in self.parameters() if p.requires_grad)
            return sum(p.numel() for p in self.parameters())
        except Exception:
            return 0

    def estimate_memory(self, training: bool = True, dtype_bytes: int = 2) -> dict:
        num_params = self.get_num_params(trainable_only=False)
        weights_mem = num_params * dtype_bytes
        grad_mem = weights_mem if training else 0
        optimizer_mem = weights_mem * 2 if training else 0
        return {
            "num_params": num_params,
            "weights_gb": weights_mem / (1024 ** 3),
            "gradients_gb": grad_mem / (1024 ** 3),
            "optimizer_gb": optimizer_mem / (1024 ** 3),
            "total_base_gb": (weights_mem + grad_mem + optimizer_mem) / (1024 ** 3),
        }
