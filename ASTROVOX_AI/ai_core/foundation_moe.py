import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional
import logging


logger = logging.getLogger(__name__)


@dataclass
class MoEConfig:
    vocab_size: int = 50257
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    num_experts: int = 8
    top_k: int = 2
    intermediate_size: int = 3072
    dropout: float = 0.1
    load_balance_loss_coef: float = 0.01
    tie_word_embeddings: bool = True


class Expert(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(hidden_size, intermediate_size)
        self.fc2 = nn.Linear(intermediate_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.GELU()

    def forward(self, x):
        return self.fc2(self.dropout(self.activation(self.fc1(x))))


class MoELayer(nn.Module):
    def __init__(self, config: MoEConfig):
        super().__init__()
        self.config = config
        self.num_experts = config.num_experts
        self.top_k = config.top_k
        self.experts = nn.ModuleList([
            Expert(config.hidden_size, config.intermediate_size, config.dropout)
            for _ in range(config.num_experts)
        ])
        self.gate = nn.Linear(config.hidden_size, config.num_experts, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        B, T, C = x.shape
        x_flat = x.view(-1, C)
        gate_logits = self.gate(x_flat)
        gate_probs = F.softmax(gate_logits, dim=-1)
        topk_probs, topk_indices = torch.topk(gate_probs, self.top_k, dim=-1)
        topk_probs = topk_probs / topk_probs.sum(dim=-1, keepdim=True)
        out = torch.zeros_like(x_flat)
        for i in range(self.top_k):
            expert_indices = topk_indices[:, i]
            expert_probs = topk_probs[:, i]
            for expert_idx in range(self.num_experts):
                mask = (expert_indices == expert_idx)
                if mask.any():
                    expert_input = x_flat[mask]
                    expert_output = self.experts[expert_idx](expert_input)
                    out[mask] += expert_output * expert_probs[mask].unsqueeze(-1)
        out = out.view(B, T, C)
        out = self.dropout(out)
        load_balance_loss = self._compute_load_balance_loss(gate_probs, topk_indices)
        return out, load_balance_loss

    def _compute_load_balance_loss(self, gate_probs, topk_indices):
        mask = torch.zeros_like(gate_probs).scatter_(1, topk_indices, 1)
        expert_load = mask.sum(dim=0)
        expert_prob_sum = (gate_probs * mask).sum(dim=0)
        load_balance_loss = self.config.load_balance_loss_coef * (expert_load.mean() - expert_prob_sum.mean()) ** 2
        return load_balance_loss


class MoEModel(nn.Module):
    def __init__(self, config: Optional[MoEConfig] = None):
        super().__init__()
        self.config = config or MoEConfig()
        self.token_emb = nn.Embedding(self.config.vocab_size, self.config.hidden_size)
        self.pos_emb = nn.Embedding(1024, self.config.hidden_size)
        self.dropout = nn.Dropout(self.config.dropout)
        self.moe_layers = nn.ModuleList([
            MoELayer(self.config) for _ in range(self.config.num_layers)
        ])
        self.ln_f = nn.LayerNorm(self.config.hidden_size)
        self.lm_head = nn.Linear(self.config.hidden_size, self.config.vocab_size, bias=False)
        if self.config.tie_word_embeddings:
            self.lm_head.weight = self.token_emb.weight
        self.apply(self._init_weights)
        logger.info("MoEModel initialized with %d experts", self.config.num_experts)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.trunc_normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)

    def forward(self, input_ids, labels=None):
        B, T = input_ids.shape
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x = self.dropout(self.token_emb(input_ids) + self.pos_emb(pos))
        total_load_balance = 0.0
        for moe_layer in self.moe_layers:
            x, lb = moe_layer(x)
            total_load_balance += lb
        x = self.ln_f(x)
        logits = self.lm_head(x)
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            lm_loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            loss = lm_loss + total_load_balance / len(self.moe_layers)
        return {"logits": logits, "loss": loss, "load_balance_loss": total_load_balance / len(self.moe_layers)}

    def route(self, hidden_states):
        with torch.no_grad():
            first_layer = self.moe_layers[0]
            gate_logits = first_layer.gate(hidden_states)
            gate_probs = F.softmax(gate_logits, dim=-1)
            topk_probs, topk_indices = torch.topk(gate_probs, self.config.top_k, dim=-1)
            return {"expert_indices": topk_indices.tolist(), "expert_weights": topk_probs.tolist()}


class MoETrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        self.step = 0
        logger.info("MoETrainer initialized")

    def train_step(self, batch):
        self.model.train()
        input_ids = batch["input_ids"].to(self.device)
        labels = batch.get("labels", input_ids).to(self.device)
        outputs = self.model(input_ids, labels=labels)
        loss = outputs["loss"]
        loss.backward()
        if self.grad_clip > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        self.optimizer.zero_grad()
        self.step += 1
        return {"loss": loss.item(), "load_balance_loss": outputs["load_balance_loss"].item(), "step": self.step}
