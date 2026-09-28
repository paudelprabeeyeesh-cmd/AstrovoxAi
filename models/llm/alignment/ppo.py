import copy
import json
import logging
import math
import os
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader, Dataset

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import get_device, set_cpu_threads
from .reward import PreferenceDataset, preference_collate_fn

logger = logging.getLogger(__name__)


def compute_log_probs(
    logits: torch.Tensor, labels: torch.Tensor, attention_mask: torch.Tensor | None = None
) -> torch.Tensor:
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    log_probs = F.log_softmax(shift_logits, dim=-1)
    token_log_probs = torch.gather(log_probs, dim=-1, index=shift_labels.unsqueeze(-1)).squeeze(-1)
    if attention_mask is not None:
        shift_mask = attention_mask[..., 1:].contiguous()
        token_log_probs = token_log_probs * shift_mask
    return token_log_probs


def compute_gae(
    rewards: torch.Tensor,
    values: torch.Tensor,
    dones: torch.Tensor,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
) -> tuple[torch.Tensor, torch.Tensor]:
    advantages = torch.zeros_like(rewards)
    last_gae = 0.0
    for t in reversed(range(rewards.size(0))):
        if dones[t]:
            last_gae = 0.0
        delta = rewards[t] + gamma * (values[t + 1] if t + 1 < values.size(0) else 0.0) - values[t]
        last_gae = delta + gamma * gae_lambda * last_gae
        advantages[t] = last_gae
    returns = advantages + values[: rewards.size(0)]
    return advantages, returns


class ValueHead(nn.Module):
    def __init__(self, hidden_size: int, device: torch.device = None, dtype: torch.dtype = None):
        super().__init__()
        if device is None:
            device = torch.device("cpu")
        if dtype is None:
            dtype = torch.float32
        self.hidden_size = hidden_size
        self.value_head = nn.Linear(hidden_size, 1, device=device, dtype=dtype)
        nn.init.zeros_(self.value_head.bias)

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        last_token_idx = (
            attention_mask.sum(dim=1) - 1 if attention_mask is not None else hidden_states.size(1) - 1
        )
        last_token_idx = (
            last_token_idx.clamp(min=0).unsqueeze(1).unsqueeze(2).expand(-1, 1, self.hidden_size)
        )
        last_hidden = hidden_states.gather(1, last_token_idx).squeeze(1)
        return self.value_head(last_hidden).squeeze(-1)


class PPOTrainer:
    def __init__(
        self,
        policy_model: nn.Module,
        value_model: nn.Module,
        tokenizer,
        config: dict[str, Any],
        reward_fn: callable | None = None,
    ):
        self.policy_model = policy_model
        self.value_model = value_model
        self.tokenizer = tokenizer
        self.config = config
        self.reward_fn = reward_fn
        self.device = get_device()
        if self.device == "cpu":
            set_cpu_threads(min(4, os.cpu_count() or 2))
        self.mp = config.get("mixed_precision", "none")
        self.dtype = torch.float32
        if self.mp == "bf16" and hasattr(torch, "bfloat16"):
            self.dtype = torch.bfloat16
        elif self.mp == "fp16" and self.device == "cuda":
            self.dtype = torch.float16
        self.policy_model.to(self.device)
        self.value_model.to(self.device)
        self.policy_optimizer = torch.optim.AdamW(
            self.policy_model.parameters(),
            lr=float(config.get("ppo_lr", 5e-6)),
            weight_decay=float(config.get("weight_decay", 0.01)),
        )
        self.value_optimizer = torch.optim.AdamW(
            self.value_model.parameters(),
            lr=float(config.get("ppo_value_lr", 5e-5)),
            weight_decay=float(config.get("weight_decay", 0.01)),
        )
        self.clip_eps = float(config.get("ppo_clip_eps", 0.2))
        self.value_clip_eps = float(config.get("ppo_value_clip_eps", 0.2))
        self.gamma = float(config.get("ppo_gamma", 0.99))
        self.gae_lambda = float(config.get("gae_lambda", 0.95))
        self.kl_coef = float(config.get("kl_coef", 0.01))
        self.entropy_coef = float(config.get("entropy_coef", 0.01))
        self.max_gen_length = int(config.get("max_gen_length", 256))
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))

    def _autocast_context(self):
        if self.mp == "bf16":
            return autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True)
        if self.mp == "fp16":
            return autocast(device_type="cuda", enabled=True)
        return autocast(device_type="cpu", dtype=torch.float32, enabled=False)

    def train_step(
        self, prompt_batch: list[str], old_policy_model: nn.Module | None = None
    ) -> dict[str, float]:
        if old_policy_model is None:
            old_policy_model = copy.deepcopy(self.policy_model)
            old_policy_model.eval()
            for param in old_policy_model.parameters():
                param.requires_grad = False
        generated_sequences, log_probs, values, rewards, masks = self._rollout(
            prompt_batch, old_policy_model
        )
        if not rewards.numel():
            return {"policy_loss": 0.0, "value_loss": 0.0, "kl": 0.0, "entropy": 0.0}
        advantages, returns = compute_gae(
            rewards, values, torch.zeros_like(rewards, dtype=torch.bool),
            gamma=self.gamma, gae_lambda=self.gae_lambda,
        )
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        flat_log_probs = log_probs.reshape(-1)
        flat_values = values[:, :-1].reshape(-1)
        flat_advantages = advantages.reshape(-1)
        flat_returns = returns.reshape(-1)
        flat_masks = masks.reshape(-1)
        flat_old_log_probs = flat_log_probs.detach()
        with self._autocast_context():
            ratio = torch.exp(flat_log_probs - flat_old_log_probs)
            ratio = torch.clamp(ratio, 0.0, 10.0)
            surr1 = ratio * flat_advantages
            surr2 = torch.clamp(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * flat_advantages
            policy_loss = -torch.min(surr1, surr2).sum() / flat_masks.sum().clamp(min=1)
            entropy_term = torch.distributions.Categorical(
                logits=flat_log_probs.unsqueeze(-1)
            ).entropy().sum()
            with torch.no_grad():
                ref_log_probs = flat_old_log_probs
            kl = compute_kl_penalty(flat_log_probs, ref_log_probs, reduction="sum")
            policy_loss = policy_loss + self.kl_coef * kl - self.entropy_coef * entropy_term
            value_pred_clipped = flat_values + torch.clamp(
                flat_values - flat_returns, -self.value_clip_eps, self.value_clip_eps
            )
            value_loss = (
                0.5
                * torch.max(
                    (flat_values - flat_returns) ** 2, (value_pred_clipped - flat_returns) ** 2
                ).sum()
                / flat_masks.sum().clamp(min=1)
            )
        total_loss = policy_loss + value_loss
        self.policy_optimizer.zero_grad(set_to_none=True)
        self.value_optimizer.zero_grad(set_to_none=True)
        if self.mp == "fp16":
            self.scaler.scale(total_loss).backward()
        else:
            total_loss.backward()
        if self.mp == "fp16":
            self.scaler.unscale_(self.policy_optimizer)
            self.scaler.unscale_(self.value_optimizer)
        nn.utils.clip_grad_norm_(
            self.policy_model.parameters(), float(self.config.get("gradient_clip_norm", 1.0))
        )
        nn.utils.clip_grad_norm_(
            self.value_model.parameters(), float(self.config.get("gradient_clip_norm", 1.0))
        )
        if self.mp == "fp16":
            self.scaler.step(self.policy_optimizer)
            self.scaler.step(self.value_optimizer)
            self.scaler.update()
        else:
            self.policy_optimizer.step()
            self.value_optimizer.step()
        return {
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "kl": kl.item(),
            "entropy": entropy_term.item(),
        }

    def _rollout(
        self, prompt_batch: list[str], old_policy_model: nn.Module
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        self.policy_model.eval()
        self.value_model.eval()
        B = len(prompt_batch)
        device = self.device
        max_gen = self.max_gen_length
        max_length = int(self.config.get("max_length", 2048))
        prompt_ids_list = []
        for prompt in prompt_batch:
            encoding = self.tokenizer.encode(prompt)
            ids = encoding.ids[:max_length]
            prompt_ids_list.append(torch.tensor(ids, dtype=torch.long, device=device))
        max_prompt_len = max(t.size(0) for t in prompt_ids_list)
        prompt_tensor = torch.zeros(B, max_prompt_len, dtype=torch.long, device=device)
        prompt_mask = torch.zeros(B, max_prompt_len, dtype=torch.long, device=device)
        for i, t in enumerate(prompt_ids_list):
            prompt_tensor[i, :t.size(0)] = t
            prompt_mask[i, :t.size(0)] = 1
        total_len = max_prompt_len + max_gen
        generated = torch.zeros(B, total_len, dtype=torch.long, device=device)
        attention_mask = torch.zeros(B, total_len, dtype=torch.long, device=device)
        generated[:, :max_prompt_len] = prompt_tensor
        attention_mask[:, :max_prompt_len] = prompt_mask
        all_log_probs = []
        all_values = []
        all_rewards = []
        step_masks = []
        for step in range(max_gen):
            current_len = max_prompt_len + step
            input_ids = generated[:, :current_len]
            mask = attention_mask[:, :current_len]
            with torch.no_grad():
                policy_outputs = old_policy_model(
                    input_ids, attention_mask=mask, use_gradient_checkpointing=False
                )
                value_outputs = self.value_model(
                    input_ids, attention_mask=mask, use_gradient_checkpointing=False
                )
            logits = policy_outputs.get("logits", policy_outputs.get("lm_logits"))
            last_logits = logits[:, -1, :]
            log_probs_step = F.log_softmax(last_logits, dim=-1)
            next_token = torch.multinomial(torch.exp(log_probs_step), num_samples=1).squeeze(-1)
            generated[:, max_prompt_len + step] = next_token
            attention_mask[:, max_prompt_len + step] = 1
            all_log_probs.append(
                log_probs_step.gather(-1, next_token.unsqueeze(-1)).squeeze(-1)
            )
            value_output = value_outputs.get("reward", value_outputs.get("logits"))
            if value_output is not None:
                v = value_output.mean(dim=-1) if value_output.dim() > 1 else value_output
            else:
                v = torch.zeros(B, device=device)
            all_values.append(v)
            step_masks.append(attention_mask[:, max_prompt_len + step])
            if self.reward_fn is not None:
                with torch.no_grad():
                    reward = self.reward_fn(generated[:, : max_prompt_len + step + 1])
                all_rewards.append(reward)
            else:
                all_rewards.append(torch.zeros(B, device=device))
        with torch.no_grad():
            terminal_logits = old_policy_model(
                generated, attention_mask=attention_mask, use_gradient_checkpointing=False
            ).get("logits", torch.zeros(B, 1, device=device))
            terminal_values = terminal_logits.mean(dim=-1).mean(dim=-1)
        all_values.append(terminal_values)
        return (
            generated,
            torch.stack(all_log_probs, dim=1),
            torch.stack(all_values, dim=1),
            torch.stack(all_rewards, dim=1),
            torch.stack(step_masks, dim=1),
        )
