import os
import json
import math
import copy
import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.cuda.amp import GradScaler, autocast

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import load_config, get_device, set_cpu_threads

logger = logging.getLogger(__name__)


def preference_collate_fn(batch, pad_token_id: int = 0):
    max_len_chosen = max(item["chosen_input_ids"].size(0) for item in batch)
    max_len_rejected = max(item["rejected_input_ids"].size(0) for item in batch)
    max_len = max(max_len_chosen, max_len_rejected)
    B = len(batch)
    chosen_input_ids = torch.zeros(B, max_len, dtype=torch.long)
    rejected_input_ids = torch.zeros(B, max_len, dtype=torch.long)
    chosen_attention_mask = torch.zeros(B, max_len, dtype=torch.long)
    rejected_attention_mask = torch.zeros(B, max_len, dtype=torch.long)
    for i, item in enumerate(batch):
        c_len = item["chosen_input_ids"].size(0)
        r_len = item["rejected_input_ids"].size(0)
        chosen_input_ids[i, :c_len] = item["chosen_input_ids"]
        rejected_input_ids[i, :r_len] = item["rejected_input_ids"]
        chosen_attention_mask[i, :c_len] = 1
        rejected_attention_mask[i, :r_len] = 1
    return {
        "chosen_input_ids": chosen_input_ids,
        "rejected_input_ids": rejected_input_ids,
        "chosen_attention_mask": chosen_attention_mask,
        "rejected_attention_mask": rejected_attention_mask,
    }


class PreferenceDataset(Dataset):
    def __init__(
        self,
        data_path: str,
        tokenizer,
        max_length: int = 2048,
        prompt_key: str = "prompt",
        chosen_key: str = "chosen",
        rejected_key: str = "rejected",
    ):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.prompt_key = prompt_key
        self.chosen_key = chosen_key
        self.rejected_key = rejected_key
        self.samples: List[Dict[str, Any]] = []
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        self.samples.append(record)
                    except json.JSONDecodeError as exc:
                        logger.warning("Skipping malformed preference line: %s", exc)
        else:
            raise FileNotFoundError(f"Preference dataset not found: {data_path}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]
        prompt = sample.get(self.prompt_key, "")
        chosen = sample.get(self.chosen_key, "")
        rejected = sample.get(self.rejected_key, "")
        if not prompt or not chosen or not rejected:
            raise ValueError(f"Sample {idx} missing required fields in dataset.")
        chosen_text = prompt + chosen
        rejected_text = prompt + rejected
        chosen_encoding = self.tokenizer.encode(chosen_text)
        rejected_encoding = self.tokenizer.encode(rejected_text)
        chosen_ids = chosen_encoding.ids[: self.max_length + 1]
        rejected_ids = rejected_encoding.ids[: self.max_length + 1]
        chosen_input_ids = torch.tensor(chosen_ids[:-1], dtype=torch.long)
        rejected_input_ids = torch.tensor(rejected_ids[:-1], dtype=torch.long)
        return {
            "chosen_input_ids": chosen_input_ids,
            "rejected_input_ids": rejected_input_ids,
        }


class RewardModel(nn.Module):
    def __init__(self, config: dict, device: torch.device = None, dtype: torch.dtype = None):
        super().__init__()
        if device is None:
            device = torch.device("cpu")
        if dtype is None:
            dtype = torch.float32
        self.config = config
        self.llm = LLM(config, device=device, dtype=dtype)
        self.hidden_size = int(config["hidden_size"])
        self.reward_head = nn.Linear(self.hidden_size, 1, device=device, dtype=dtype)
        nn.init.zeros_(self.reward_head.bias)
        self.to(device)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        use_gradient_checkpointing: bool = False,
    ) -> Dict[str, torch.Tensor]:
        outputs = self.llm(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_gradient_checkpointing=use_gradient_checkpointing,
        )
        hidden_states = outputs["logits"]
        last_token_idx = attention_mask.sum(dim=1) - 1 if attention_mask is not None else input_ids.size(1) - 1
        last_token_idx = last_token_idx.clamp(min=0).unsqueeze(1).unsqueeze(2).expand(-1, 1, self.hidden_size)
        last_hidden = hidden_states.gather(1, last_token_idx).squeeze(1)
        reward = self.reward_head(last_hidden).squeeze(-1)
        return {"reward": reward, "logits": hidden_states}


def compute_kl_penalty(
    log_policy: torch.Tensor,
    log_reference: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
    reduction: str = "mean",
) -> torch.Tensor:
    kl_per_token = log_policy - log_reference
    if attention_mask is not None:
        kl_per_token = kl_per_token * attention_mask
        if reduction == "mean":
            return kl_per_token.sum() / attention_mask.sum().clamp(min=1)
        if reduction == "sum":
            return kl_per_token.sum()
    if reduction == "mean":
        return kl_per_token.mean()
    if reduction == "sum":
        return kl_per_token.sum()
    return kl_per_token


def compute_log_probs(
    logits: torch.Tensor,
    labels: torch.Tensor,
    attention_mask: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    shift_logits = logits[:, :-1, :]
    shift_labels = labels[:, 1:]
    log_probs = F.log_softmax(shift_logits, dim=-1)
    token_log_probs = torch.gather(log_probs, dim=-1, index=shift_labels.unsqueeze(-1)).squeeze(-1)
    if attention_mask is not None:
        shift_mask = attention_mask[:, 1:]
        token_log_probs = token_log_probs * shift_mask
    return token_log_probs


def _get_policy_log_probs(
    model: nn.Module,
    input_ids: torch.Tensor,
    attention_mask: Optional[torch.Tensor],
    use_gradient_checkpointing: bool = False,
) -> Tuple[torch.Tensor, torch.Tensor]:
    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        use_gradient_checkpointing=use_gradient_checkpointing,
    )
    logits = outputs.get("logits", outputs.get("lm_logits"))
    labels = input_ids
    log_probs = compute_log_probs(logits, labels, attention_mask)
    return log_probs.sum(dim=-1), logits


class AlignmentTrainer:
    def __init__(
        self,
        model: nn.Module,
        tokenizer,
        config: Dict[str, Any],
        reference_model: Optional[nn.Module] = None,
    ):
        self.model = model
        self.reference_model = reference_model
        self.tokenizer = tokenizer
        self.config = config
        self.device = get_device()
        if self.device == "cpu":
            set_cpu_threads(min(4, os.cpu_count() or 2))
        self.mp = config.get("mixed_precision", "none")
        self.dtype = torch.float32
        if self.mp == "bf16" and hasattr(torch, "bfloat16"):
            self.dtype = torch.bfloat16
        elif self.mp == "fp16" and self.device == "cuda":
            self.dtype = torch.float16
        self.beta = float(config.get("beta", 0.1))
        self.kl_coef = float(config.get("kl_coef", 0.01))
        self.label_smoothing = float(config.get("label_smoothing", 0.0))
        self.max_length = int(config.get("max_length", 2048))
        self.model.to(self.device)
        if self.reference_model is not None:
            self.reference_model.to(self.device)
            self.reference_model.eval()
            for param in self.reference_model.parameters():
                param.requires_grad = False
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))

    def _autocast_context(self):
        if self.mp == "bf16":
            return autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True)
        if self.mp == "fp16":
            return autocast(device_type="cuda", enabled=True)
        return autocast(device_type="cpu", dtype=torch.float32, enabled=False)

    def train_dpo(
        self,
        train_dataset: PreferenceDataset,
        output_dir: str,
        val_dataset: Optional[PreferenceDataset] = None,
    ) -> Dict[str, float]:
        if self.reference_model is None:
            raise ValueError("Reference model is required for DPO.")
        return self._train_preference(
            method="dpo",
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            output_dir=output_dir,
        )

    def train_orpo(
        self,
        train_dataset: PreferenceDataset,
        output_dir: str,
        val_dataset: Optional[PreferenceDataset] = None,
    ) -> Dict[str, float]:
        return self._train_preference(
            method="orpo",
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            output_dir=output_dir,
        )

    def train_simpo(
        self,
        train_dataset: PreferenceDataset,
        output_dir: str,
        val_dataset: Optional[PreferenceDataset] = None,
    ) -> Dict[str, float]:
        if self.reference_model is not None:
            logger.info("SimPO selected: ignoring provided reference model.")
        return self._train_preference(
            method="simpo",
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            output_dir=output_dir,
        )

    def train_reward_model(
        self,
        train_dataset: PreferenceDataset,
        output_dir: str,
        val_dataset: Optional[PreferenceDataset] = None,
    ) -> Dict[str, float]:
        if not isinstance(self.model, RewardModel):
            raise TypeError("For reward model training, provide a RewardModel instance as `model`.")
        return self._train_reward_model(
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            output_dir=output_dir,
        )

    def _train_preference(
        self,
        method: str,
        train_dataset: PreferenceDataset,
        output_dir: str,
        val_dataset: Optional[PreferenceDataset] = None,
    ) -> Dict[str, float]:
        batch_size = int(self.config.get("preference_batch_size", 2))
        epochs = int(self.config.get("preference_epochs", 1))
        lr = float(self.config.get("preference_lr", 5e-6))
        weight_decay = float(self.config.get("weight_decay", 0.01))
        grad_clip = float(self.config.get("gradient_clip_norm", 1.0))
        accumulation = int(self.config.get("gradient_accumulation_steps", 1))
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=len(train_dataset) // batch_size * epochs, eta_min=self.config.get("min_lr", 1e-7)
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            collate_fn=lambda b: preference_collate_fn(b, pad_token_id=self.tokenizer.token_to_id("<pad>") or 0),
            drop_last=True,
        )
        val_loader = None
        if val_dataset is not None and len(val_dataset) > 0:
            val_loader = DataLoader(
                val_dataset,
                batch_size=max(1, batch_size // 2),
                shuffle=False,
                num_workers=0,
                collate_fn=lambda b: preference_collate_fn(b, pad_token_id=self.tokenizer.token_to_id("<pad>") or 0),
                drop_last=False,
            )
        best_loss = float("inf")
        global_step = 0
        for epoch in range(epochs):
            self.model.train()
            train_loss_sum = 0.0
            train_batches = 0
            for batch in train_loader:
                chosen_ids = batch["chosen_input_ids"].to(self.device, non_blocking=True)
                rejected_ids = batch["rejected_input_ids"].to(self.device, non_blocking=True)
                chosen_mask = batch["chosen_attention_mask"].to(self.device, non_blocking=True)
                rejected_mask = batch["rejected_attention_mask"].to(self.device, non_blocking=True)
                loss, metrics = self._preference_step(
                    chosen_ids=chosen_ids,
                    rejected_ids=rejected_ids,
                    chosen_mask=chosen_mask,
                    rejected_mask=rejected_mask,
                    method=method,
                )
                if self.mp == "fp16":
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()
                train_loss_sum += loss.item()
                train_batches += 1
                if (train_batches % accumulation) == 0:
                    if grad_clip > 0:
                        if self.mp == "fp16":
                            self.scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip)
                    if self.mp == "fp16":
                        self.scaler.step(optimizer)
                        self.scaler.update()
                    else:
                        optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    if scheduler is not None:
                        scheduler.step()
                    global_step += 1
                    if global_step % 100 == 0:
                        logger.info(
                            "Step %d | Method=%s | loss=%.4f | %s",
                            global_step,
                            method.upper(),
                            loss.item(),
                            " | ".join(f"{k}={v:.4f}" for k, v in metrics.items()),
                        )
            avg_train_loss = train_loss_sum / max(train_batches, 1)
            val_metrics = self._validate_preference(val_loader, method) if val_loader is not None else {}
            log_msg = f"Epoch {epoch + 1}/{epochs} | {method.upper()} Train loss: {avg_train_loss:.4f}"
            if val_metrics:
                log_msg += f" | Val loss: {val_metrics['val_loss']:.4f}"
            logger.info(log_msg)
            val_loss = val_metrics.get("val_loss", avg_train_loss)
            if val_loss < best_loss:
                best_loss = val_loss
                self._save_checkpoint(output_dir, method, epoch, best_loss)
        self._save_final(output_dir, method)
        logger.info("Preference training complete. Best loss: %.4f", best_loss)
        return {"best_loss": best_loss}

    def _train_reward_model(
        self,
        train_dataset: PreferenceDataset,
        output_dir: str,
        val_dataset: Optional[PreferenceDataset] = None,
    ) -> Dict[str, float]:
        batch_size = int(self.config.get("preference_batch_size", 2))
        epochs = int(self.config.get("preference_epochs", 1))
        lr = float(self.config.get("preference_lr", 5e-5))
        weight_decay = float(self.config.get("weight_decay", 0.01))
        grad_clip = float(self.config.get("gradient_clip_norm", 1.0))
        accumulation = int(self.config.get("gradient_accumulation_steps", 1))
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=len(train_dataset) // batch_size * epochs, eta_min=self.config.get("min_lr", 1e-7)
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            collate_fn=lambda b: preference_collate_fn(b, pad_token_id=self.tokenizer.token_to_id("<pad>") or 0),
            drop_last=True,
        )
        val_loader = None
        if val_dataset is not None and len(val_dataset) > 0:
            val_loader = DataLoader(
                val_dataset,
                batch_size=max(1, batch_size // 2),
                shuffle=False,
                num_workers=0,
                collate_fn=lambda b: preference_collate_fn(b, pad_token_id=self.tokenizer.token_to_id("<pad>") or 0),
                drop_last=False,
            )
        best_loss = float("inf")
        global_step = 0
        margin = float(self.config.get("reward_margin", 0.5))
        for epoch in range(epochs):
            self.model.train()
            train_loss_sum = 0.0
            train_batches = 0
            for batch in train_loader:
                chosen_ids = batch["chosen_input_ids"].to(self.device, non_blocking=True)
                rejected_ids = batch["rejected_input_ids"].to(self.device, non_blocking=True)
                chosen_mask = batch["chosen_attention_mask"].to(self.device, non_blocking=True)
                rejected_mask = batch["rejected_attention_mask"].to(self.device, non_blocking=True)
                with self._autocast_context():
                    chosen_outputs = self.model(chosen_ids, attention_mask=chosen_mask, use_gradient_checkpointing=True)
                    rejected_outputs = self.model(rejected_ids, attention_mask=rejected_mask, use_gradient_checkpointing=True)
                    chosen_reward = chosen_outputs["reward"]
                    rejected_reward = rejected_outputs["reward"]
                    loss = -F.logsigmoid(chosen_reward - rejected_reward - margin).mean()
                if self.mp == "fp16":
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()
                train_loss_sum += loss.item()
                train_batches += 1
                if (train_batches % accumulation) == 0:
                    if grad_clip > 0:
                        if self.mp == "fp16":
                            self.scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip)
                    if self.mp == "fp16":
                        self.scaler.step(optimizer)
                        self.scaler.update()
                    else:
                        optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    if scheduler is not None:
                        scheduler.step()
                    global_step += 1
                    if global_step % 100 == 0:
                        logger.info("Step %d | Reward train loss: %.4f", global_step, loss.item())
            avg_train_loss = train_loss_sum / max(train_batches, 1)
            val_loss = self._validate_reward(val_loader) if val_loader is not None else {}
            log_msg = f"Epoch {epoch + 1}/{epochs} | Reward Train loss: {avg_train_loss:.4f}"
            if val_loss:
                log_msg += f" | Val loss: {val_loss['val_loss']:.4f}"
            logger.info(log_msg)
            val_loss_val = val_loss.get("val_loss", avg_train_loss)
            if val_loss_val < best_loss:
                best_loss = val_loss_val
                self._save_checkpoint(output_dir, "reward", epoch, best_loss)
        self._save_final(output_dir, "reward")
        logger.info("Reward model training complete. Best loss: %.4f", best_loss)
        return {"best_loss": best_loss}

    def _preference_step(
        self,
        chosen_ids: torch.Tensor,
        rejected_ids: torch.Tensor,
        chosen_mask: torch.Tensor,
        rejected_mask: torch.Tensor,
        method: str,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        with self._autocast_context():
            policy_chosen_log_probs_sum, policy_chosen_logits = _get_policy_log_probs(
                self.model, chosen_ids, chosen_mask, use_gradient_checkpointing=True
            )
            policy_rejected_log_probs_sum, policy_rejected_logits = _get_policy_log_probs(
                self.model, rejected_ids, rejected_mask, use_gradient_checkpointing=True
            )
            policy_chosen_log_probs = compute_log_probs(policy_chosen_logits, chosen_ids, chosen_mask)
            policy_rejected_log_probs = compute_log_probs(policy_rejected_logits, rejected_ids, rejected_mask)
            if method == "dpo":
                if self.reference_model is None:
                    raise ValueError("Reference model is required for DPO.")
                with torch.no_grad():
                    ref_chosen_log_probs_sum, ref_chosen_logits = _get_policy_log_probs(
                        self.reference_model, chosen_ids, chosen_mask
                    )
                    ref_rejected_log_probs_sum, ref_rejected_logits = _get_policy_log_probs(
                        self.reference_model, rejected_ids, rejected_mask
                    )
                pi_log_ratio_chosen = policy_chosen_log_probs.sum(dim=-1) - ref_chosen_log_probs_sum
                pi_log_ratio_rejected = policy_rejected_log_probs.sum(dim=-1) - ref_rejected_log_probs_sum
                logits = self.beta * (pi_log_ratio_chosen - pi_log_ratio_rejected)
                loss = -F.logsigmoid(logits).mean()
                kl_loss = compute_kl_penalty(
                    policy_chosen_log_probs,
                    compute_log_probs(ref_chosen_logits.detach(), chosen_ids, chosen_mask),
                    attention_mask=chosen_mask,
                    reduction="mean",
                ) + compute_kl_penalty(
                    policy_rejected_log_probs,
                    compute_log_probs(ref_rejected_logits.detach(), rejected_ids, rejected_mask),
                    attention_mask=rejected_mask,
                    reduction="mean",
                )
                loss = loss + self.kl_coef * kl_loss
                metrics = {"dpo_loss": loss.item(), "kl": kl_loss.item()}
            elif method == "orpo":
                log_odds = policy_chosen_log_probs.sum(dim=-1) - policy_rejected_log_probs.sum(dim=-1)
                loss = -F.logsigmoid(self.beta * log_odds).mean()
                kl_loss = compute_kl_penalty(
                    policy_chosen_log_probs,
                    F.log_softmax(policy_chosen_logits.detach(), dim=-1),
                    attention_mask=chosen_mask,
                    reduction="mean",
                )
                loss = loss + self.kl_coef * kl_loss
                metrics = {"orpo_loss": loss.item(), "kl": kl_loss.item()}
            elif method == "simpo":
                log_ratio = policy_chosen_log_probs.sum(dim=-1) - policy_rejected_log_probs.sum(dim=-1)
                gamma = float(self.config.get("simpo_gamma", self.beta))
                margin = float(self.config.get("simpo_margin", 0.0))
                loss = -F.logsigmoid(gamma * log_ratio - margin).mean()
                metrics = {"simpo_loss": loss.item()}
            else:
                raise ValueError(f"Unknown preference method: {method}")
        return loss, metrics

    def _validate_preference(self, val_loader: DataLoader, method: str) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        batches = 0
        with torch.no_grad():
            for batch in val_loader:
                chosen_ids = batch["chosen_input_ids"].to(self.device, non_blocking=True)
                rejected_ids = batch["rejected_input_ids"].to(self.device, non_blocking=True)
                chosen_mask = batch["chosen_attention_mask"].to(self.device, non_blocking=True)
                rejected_mask = batch["rejected_attention_mask"].to(self.device, non_blocking=True)
                loss, _ = self._preference_step(
                    chosen_ids=chosen_ids,
                    rejected_ids=rejected_ids,
                    chosen_mask=chosen_mask,
                    rejected_mask=rejected_mask,
                    method=method,
                )
                total_loss += loss.item()
                batches += 1
        avg = total_loss / max(batches, 1)
        return {"val_loss": avg}

    def _validate_reward(self, val_loader: DataLoader) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        batches = 0
        margin = float(self.config.get("reward_margin", 0.5))
        with torch.no_grad():
            for batch in val_loader:
                chosen_ids = batch["chosen_input_ids"].to(self.device, non_blocking=True)
                rejected_ids = batch["rejected_input_ids"].to(self.device, non_blocking=True)
                chosen_mask = batch["chosen_attention_mask"].to(self.device, non_blocking=True)
                rejected_mask = batch["rejected_attention_mask"].to(self.device, non_blocking=True)
                with self._autocast_context():
                    chosen_outputs = self.model(chosen_ids, attention_mask=chosen_mask)
                    rejected_outputs = self.model(rejected_ids, attention_mask=rejected_mask)
                    chosen_reward = chosen_outputs["reward"]
                    rejected_reward = rejected_outputs["reward"]
                    loss = -F.logsigmoid(chosen_reward - rejected_reward - margin).mean()
                total_loss += loss.item()
                batches += 1
        avg = total_loss / max(batches, 1)
        return {"val_loss": avg}

    def _save_checkpoint(self, output_dir: str, method: str, epoch: int, best_loss: float) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_best.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {
                "epoch": epoch,
                "method": method,
                "best_loss": best_loss,
                "model_state_dict": unwrapped.state_dict(),
                "config": self.config,
            },
            path,
        )
        logger.info("Saved best checkpoint for %s to %s", method.upper(), path)

    def _save_final(self, output_dir: str, method: str) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_final.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {
                "method": method,
                "model_state_dict": unwrapped.state_dict(),
                "config": self.config,
            },
            path,
        )
        logger.info("Saved final checkpoint for %s to %s", method.upper(), path)


class PPOTrainer:
    def __init__(
        self,
        policy_model: nn.Module,
        value_model: nn.Module,
        tokenizer,
        config: Dict[str, Any],
        reward_fn: Optional[callable] = None,
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
        self.policy_optimizer = torch.optim.AdamW(self.policy_model.parameters(), lr=float(config.get("ppo_lr", 5e-6)), weight_decay=float(config.get("weight_decay", 0.01)))
        self.value_optimizer = torch.optim.AdamW(self.value_model.parameters(), lr=float(config.get("ppo_value_lr", 5e-5)), weight_decay=float(config.get("weight_decay", 0.01)))
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

    def _compute_gae(
        self,
        rewards: torch.Tensor,
        values: torch.Tensor,
        dones: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        advantages = torch.zeros_like(rewards)
        last_gae = 0.0
        for t in reversed(range(rewards.size(0))):
            if dones[t]:
                last_gae = 0.0
            delta = rewards[t] + self.gamma * (values[t + 1] if t + 1 < values.size(0) else 0) - values[t]
            last_gae = delta + self.gamma * self.gae_lambda * last_gae
            advantages[t] = last_gae
        returns = advantages + values[:-1] if values.size(0) > advantages.size(0) else advantages + values
        return advantages, returns

    def train_step(self, prompt_batch: List[str], old_policy_model: Optional[nn.Module] = None) -> Dict[str, float]:
        if old_policy_model is None:
            old_policy_model = copy.deepcopy(self.policy_model)
            old_policy_model.eval()
            for param in old_policy_model.parameters():
                param.requires_grad = False
        generated_sequences, log_probs, values, rewards, masks = self._rollout(prompt_batch, old_policy_model)
        if not rewards.numel():
            return {"policy_loss": 0.0, "value_loss": 0.0, "kl": 0.0}
        advantages, returns = self._compute_gae(rewards, values, torch.zeros_like(rewards, dtype=torch.bool))
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        flat_log_probs = log_probs.reshape(-1)
        flat_values = values[:-1].reshape(-1)
        flat_advantages = advantages.reshape(-1)
        flat_returns = returns.reshape(-1)
        flat_masks = masks.reshape(-1)
        flat_old_log_probs = flat_log_probs.detach()
        with self._autocast_context():
            new_log_probs = flat_log_probs
            ratio = torch.exp(new_log_probs - flat_old_log_probs)
            ratio = torch.clamp(ratio, 0.0, 10.0)
            surr1 = ratio * flat_advantages
            surr2 = torch.clamp(ratio, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * flat_advantages
            policy_loss = -torch.min(surr1, surr2).sum() / flat_masks.sum().clamp(min=1)
            entropy = torch.distributions.Categorical(logits=flat_log_probs.unsqueeze(-1)).entropy().sum()
            if old_policy_model is not None:
                with torch.no_grad():
                    ref_log_probs = flat_old_log_probs
                kl = compute_kl_penalty(new_log_probs, ref_log_probs, reduction="sum")
                policy_loss = policy_loss + self.kl_coef * kl
            else:
                kl = torch.tensor(0.0, device=self.device)
            policy_loss = policy_loss - self.entropy_coef * entropy
            new_values = flat_values
            value_pred_clipped = flat_values + torch.clamp(new_values - flat_values, -self.value_clip_eps, self.value_clip_eps)
            value_loss = 0.5 * torch.max((new_values - flat_returns) ** 2, (value_pred_clipped - flat_returns) ** 2).sum() / flat_masks.sum().clamp(min=1)
        self.policy_optimizer.zero_grad(set_to_none=True)
        self.value_optimizer.zero_grad(set_to_none=True)
        if self.mp == "fp16":
            self.scaler.scale(policy_loss + value_loss).backward()
        else:
            (policy_loss + value_loss).backward()
        if self.mp == "fp16":
            self.scaler.unscale_(self.policy_optimizer)
            self.scaler.unscale_(self.value_optimizer)
        torch.nn.utils.clip_grad_norm_(self.policy_model.parameters(), float(self.config.get("gradient_clip_norm", 1.0)))
        torch.nn.utils.clip_grad_norm_(self.value_model.parameters(), float(self.config.get("gradient_clip_norm", 1.0)))
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
            "kl": kl.item() if torch.is_tensor(kl) else float(kl),
        }

    def _rollout(self, prompt_batch: List[str], old_policy_model: nn.Module) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        self.policy_model.eval()
        self.value_model.eval()
        B = len(prompt_batch)
        device = self.device
        max_len = self.max_gen_length
        prompt_ids_list = []
        for prompt in prompt_batch:
            encoding = self.tokenizer.encode(prompt)
            ids = encoding.ids[: self.config.get("max_length", 2048)]
            prompt_ids_list.append(torch.tensor(ids, dtype=torch.long, device=device))
        max_prompt_len = max(t.size(0) for t in prompt_ids_list)
        prompt_tensor = torch.zeros(B, max_prompt_len, dtype=torch.long, device=device)
        prompt_mask = torch.zeros(B, max_prompt_len, dtype=torch.long, device=device)
        for i, t in enumerate(prompt_ids_list):
            prompt_tensor[i, : t.size(0)] = t
            prompt_mask[i, : t.size(0)] = 1
        generated = torch.zeros(B, max_prompt_len + max_len, dtype=torch.long, device=device)
        attention_mask = torch.zeros(B, max_prompt_len + max_len, dtype=torch.long, device=device)
        generated[:, :max_prompt_len] = prompt_tensor
        attention_mask[:, :max_prompt_len] = prompt_mask
        all_log_probs = []
        all_values = []
        all_rewards = []
        step_masks = []
        for step in range(max_len):
            input_ids = generated[:, : max_prompt_len + step]
            mask = attention_mask[:, : max_prompt_len + step]
            with torch.no_grad():
                policy_outputs = old_policy_model(input_ids, attention_mask=mask, use_gradient_checkpointing=False)
                value_outputs = self.value_model(input_ids, attention_mask=mask, use_gradient_checkpointing=False)
            logits = policy_outputs["logits"]
            last_logits = logits[:, -1, :]
            log_probs_step = F.log_softmax(last_logits, dim=-1)
            next_token = torch.multinomial(torch.exp(log_probs_step), num_samples=1).squeeze(-1)
            generated[:, max_prompt_len + step] = next_token
            attention_mask[:, max_prompt_len + step] = 1
            all_log_probs.append(log_probs_step.gather(-1, next_token.unsqueeze(-1)).squeeze(-1))
            value = value_outputs.get("reward", value_outputs.get("logits", torch.zeros(B, device=device))).mean(dim=-1)
            all_values.append(value)
            step_masks.append(attention_mask[:, max_prompt_len + step])
            if self.reward_fn is not None:
                with torch.no_grad():
                    reward = self.reward_fn(generated[:, : max_prompt_len + step + 1])
                all_rewards.append(reward)
            else:
                all_rewards.append(torch.zeros(B, device=device))
        with torch.no_grad():
            terminal_values = torch.zeros(B, device=device)
            terminal_logits = old_policy_model(generated, attention_mask=attention_mask, use_gradient_checkpointing=False).get("logits", torch.zeros(B, 1, device=device))
            terminal_values = terminal_logits.mean(dim=-1).mean(dim=-1)
        all_values.append(terminal_values)
        return generated, torch.stack(all_log_probs, dim=1), torch.stack(all_values, dim=1), torch.stack(all_rewards, dim=1), torch.stack(step_masks, dim=1)


class AlignmentPipeline:
    def __init__(self, config_path: str = "models/llm/configs/config_4b.yaml"):
        self.config = load_config(config_path)
        self.device = get_device()
        if self.device == "cpu":
            set_cpu_threads(min(4, os.cpu_count() or 2))
        self.mp = self.config.get("mixed_precision", "none")
        self.dtype = torch.float32
        if self.mp == "bf16" and hasattr(torch, "bfloat16"):
            self.dtype = torch.bfloat16
        elif self.mp == "fp16" and self.device == "cuda":
            self.dtype = torch.float16

    def run_dpo(self, resume_from: Optional[str] = None) -> Dict[str, float]:
        return self._run_preference_method(method="dpo", resume_from=resume_from)

    def run_orpo(self, resume_from: Optional[str] = None) -> Dict[str, float]:
        return self._run_preference_method(method="orpo", resume_from=resume_from)

    def run_simpo(self, resume_from: Optional[str] = None) -> Dict[str, float]:
        return self._run_preference_method(method="simpo", resume_from=resume_from)

    def run_reward_training(self, resume_from: Optional[str] = None) -> Dict[str, float]:
        train_file = self.config.get("preference_train_file", self.config.get("train_file", "data/preferences.jsonl"))
        val_file = self.config.get("preference_val_file", train_file)
        if not os.path.exists(train_file):
            raise FileNotFoundError(f"Preference train file not found: {train_file}")
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        train_dataset = PreferenceDataset(train_file, tokenizer, max_length=self.config.get("max_length", 2048))
        val_dataset = PreferenceDataset(val_file, tokenizer, max_length=self.config.get("max_length", 2048)) if os.path.exists(val_file) else None
        reward_model = RewardModel(self.config, device=torch.device(self.device), dtype=self.dtype)
        if resume_from and os.path.exists(resume_from):
            state = torch.load(resume_from, map_location=self.device, weights_only=False)
            reward_model.load_state_dict(state["model_state_dict"], strict=False)
        trainer = AlignmentTrainer(reward_model, tokenizer, self.config)
        return trainer.train_reward_model(train_dataset, self.config.get("output_dir", "reward_model"), val_dataset=val_dataset)

    def _run_preference_method(self, method: str, resume_from: Optional[str] = None) -> Dict[str, float]:
        train_file = self.config.get("preference_train_file", self.config.get("train_file", "data/preferences.jsonl"))
        val_file = self.config.get("preference_val_file", train_file)
        if not os.path.exists(train_file):
            raise FileNotFoundError(f"Preference train file not found: {train_file}")
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        train_dataset = PreferenceDataset(train_file, tokenizer, max_length=self.config.get("max_length", 2048))
        val_dataset = PreferenceDataset(val_file, tokenizer, max_length=self.config.get("max_length", 2048)) if os.path.exists(val_file) else None
        model = LLM(self.config, device=torch.device(self.device), dtype=self.dtype)
        if resume_from and os.path.exists(resume_from):
            state = torch.load(resume_from, map_location=self.device, weights_only=False)
            model.load_state_dict(state["model_state_dict"], strict=False)
        reference_model = None
        if method == "dpo":
            reference_model = LLM(self.config, device=torch.device(self.device), dtype=self.dtype)
            if resume_from and os.path.exists(resume_from):
                reference_model.load_state_dict(state["model_state_dict"], strict=False)
            reference_model.eval()
            for param in reference_model.parameters():
                param.requires_grad = False
        trainer = AlignmentTrainer(model, tokenizer, self.config, reference_model=reference_model)
        train_fn = {
            "dpo": trainer.train_dpo,
            "orpo": trainer.train_orpo,
            "simpo": trainer.train_simpo,
        }.get(method)
        if train_fn is None:
            raise ValueError(f"Unsupported alignment method: {method}")
        return train_fn(train_dataset, self.config.get("output_dir", "alignment_output"), val_dataset=val_dataset)
