import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional
import logging

from .transformers.transformer_from_scratch import TransformerFromScratch, TransformerConfig

logger = logging.getLogger(__name__)


@dataclass
class ReasoningConfig:
    vocab_size: int = 50257
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    intermediate_size: int = 3072
    max_position_embeddings: int = 2048
    dropout: float = 0.1
    num_reasoning_steps: int = 4
    tie_word_embeddings: bool = True


class ReasoningModel(nn.Module):
    def __init__(self, config: Optional[ReasoningConfig] = None):
        super().__init__()
        self.config = config or ReasoningConfig()
        t_config = TransformerConfig(
            vocab_size=self.config.vocab_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            num_heads=self.config.num_heads,
            intermediate_size=self.config.intermediate_size,
            max_position_embeddings=self.config.max_position_embeddings,
            dropout=self.config.dropout,
        )
        self.transformer = TransformerFromScratch(t_config)
        self.reasoning_head = nn.Linear(self.config.hidden_size, self.config.hidden_size)
        self.step_gate = nn.Linear(self.config.hidden_size, 1)
        self.lm_head = nn.Linear(self.config.hidden_size, self.config.vocab_size, bias=False)
        if self.config.tie_word_embeddings:
            self.lm_head.weight = self.transformer.token_emb.weight
        self.apply(self._init_weights)
        logger.info("Reasoning model initialized")

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

    def forward(self, input_ids, labels=None, reasoning_labels=None):
        hidden = self.transformer(input_ids)
        logits = self.lm_head(hidden)
        step_logits = self.step_gate(hidden)
        loss = None
        if labels is not None:
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            loss = F.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        reasoning_loss = None
        if reasoning_labels is not None:
            reasoning_loss = F.binary_cross_entropy_with_logits(step_logits.squeeze(-1), reasoning_labels.float())
            if loss is not None:
                loss = loss + reasoning_loss
        return {"logits": logits, "loss": loss, "hidden": hidden, "step_logits": step_logits}

    def chain_of_thought(self, prompt, max_new_tokens=100):
        self.eval()
        input_ids = prompt
        steps = []
        for step in range(self.config.num_reasoning_steps):
            outputs = self.forward(input_ids)
            hidden = outputs["hidden"]
            step_logit = outputs["step_logits"][:, -1, :]
            step_prob = torch.sigmoid(step_logit).item()
            steps.append({"step": step, "confidence": step_prob, "hidden_norm": hidden[:, -1, :].norm().item()})
            next_token = outputs["logits"][:, -1, :].argmax(dim=-1, keepdim=True)
            input_ids = torch.cat([input_ids, next_token], dim=1)
            if next_token.item() == 0:
                break
        return {"sequence": input_ids, "steps": steps}


class ReasoningTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        self.step = 0
        logger.info("ReasoningTrainer initialized")

    def train_step(self, batch):
        self.model.train()
        input_ids = batch["input_ids"].to(self.device)
        labels = batch.get("labels", input_ids).to(self.device)
        reasoning_labels = batch.get("reasoning_labels")
        if reasoning_labels is not None:
            reasoning_labels = reasoning_labels.to(self.device)
        outputs = self.model(input_ids, labels=labels, reasoning_labels=reasoning_labels)
        loss = outputs["loss"]
        loss.backward()
        if self.grad_clip > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        self.optimizer.zero_grad()
        self.step += 1
        return {"loss": loss.item(), "step": self.step}
