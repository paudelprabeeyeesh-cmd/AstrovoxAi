import json
import logging
import os
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

try:
    from torch.amp import GradScaler, autocast
except ImportError:
    from torch.cuda.amp import GradScaler, autocast

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


def get_sequence_log_prob(
    model: nn.Module,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor | None,
    use_gradient_checkpointing: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        use_gradient_checkpointing=use_gradient_checkpointing,
    )
    logits = outputs.get("logits", outputs.get("lm_logits"))
    if logits is None:
        raise ValueError("Model outputs missing logits.")
    log_probs = compute_log_probs(logits, input_ids, attention_mask)
    return log_probs.sum(dim=-1), logits


def compute_kl_penalty(
    log_policy: torch.Tensor,
    log_reference: torch.Tensor,
    attention_mask: torch.Tensor | None = None,
    reduction: str = "mean",
) -> torch.Tensor:
    kl_per_token = log_policy - log_reference
    if attention_mask is not None:
        if attention_mask.shape[-1] != kl_per_token.shape[-1]:
            attention_mask = attention_mask[..., 1:]
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


class ORPOTrainer:
    def __init__(
        self,
        model: nn.Module,
        tokenizer,
        config: dict[str, Any],
        train_dataset: PreferenceDataset | None = None,
        val_dataset: PreferenceDataset | None = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
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
        self.model.to(self.device)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=float(config.get("orpo_lr", 5e-6)),
            weight_decay=float(config.get("weight_decay", 0.01)),
        )
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))

    def _autocast_context(self):
        if self.mp == "bf16":
            return autocast("cpu", dtype=torch.bfloat16, enabled=True)
        if self.mp == "fp16":
            return autocast("cuda", enabled=True)
        return autocast("cpu", dtype=torch.float32, enabled=False)

    def _orpo_loss(
        self,
        chosen_ids: torch.Tensor,
        rejected_ids: torch.Tensor,
        chosen_mask: torch.Tensor,
        rejected_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, dict[str, float]]:
        with self._autocast_context():
            policy_chosen_log_probs_sum, policy_chosen_logits = get_sequence_log_prob(
                self.model, chosen_ids, chosen_mask, use_gradient_checkpointing=True
            )
            policy_rejected_log_probs_sum, policy_rejected_logits = get_sequence_log_prob(
                self.model, rejected_ids, rejected_mask, use_gradient_checkpointing=True
            )
            log_odds = policy_chosen_log_probs_sum - policy_rejected_log_probs_sum
            loss = -F.logsigmoid(self.beta * log_odds).mean()
            kl_chosen = compute_kl_penalty(
                compute_log_probs(policy_chosen_logits, chosen_ids, chosen_mask),
                compute_log_probs(policy_chosen_logits.detach(), chosen_ids, chosen_mask),
                attention_mask=chosen_mask,
                reduction="mean",
            )
            kl_rejected = compute_kl_penalty(
                compute_log_probs(policy_rejected_logits, rejected_ids, rejected_mask),
                compute_log_probs(policy_rejected_logits.detach(), rejected_ids, rejected_mask),
                attention_mask=rejected_mask,
                reduction="mean",
            )
            kl_loss = kl_chosen + kl_rejected
            if not torch.isfinite(kl_loss):
                kl_loss = torch.tensor(0.0, device=loss.device, dtype=loss.dtype)
            loss = loss + self.kl_coef * kl_loss
            loss = torch.nan_to_num(loss, nan=0.0, posinf=100.0, neginf=-100.0)
            loss = torch.clamp(loss, -100.0, 100.0)
            metrics = {"orpo_loss": loss.item(), "kl": kl_loss.item(), "log_odds": log_odds.mean().item()}
        return loss, metrics

    def train(self, output_dir: str, epochs: int | None = None) -> dict[str, float]:
        epochs = epochs if epochs is not None else int(self.config.get("orpo_epochs", 1))
        batch_size = int(self.config.get("preference_batch_size", 2))
        grad_clip = float(self.config.get("gradient_clip_norm", 1.0))
        accumulation = int(self.config.get("gradient_accumulation_steps", 1))
        pad_token_id = self.tokenizer.token_to_id("<pad>") or 0
        max_length = int(self.config.get("max_length", 2048))

        train_loader = DataLoader(
            self.train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            collate_fn=lambda b: preference_collate_fn(b, pad_token_id=pad_token_id, max_length=max_length),
            drop_last=True,
        )
        val_loader = None
        if self.val_dataset is not None and len(self.val_dataset) > 0:
            val_loader = DataLoader(
                self.val_dataset,
                batch_size=max(1, batch_size // 2),
                shuffle=False,
                num_workers=0,
                collate_fn=lambda b: preference_collate_fn(b, pad_token_id=pad_token_id, max_length=max_length),
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
                loss, metrics = self._orpo_loss(chosen_ids, rejected_ids, chosen_mask, rejected_mask)
                if self.mp == "fp16":
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()
                train_loss_sum += loss.item()
                train_batches += 1
                if train_batches % accumulation == 0:
                    if grad_clip > 0:
                        if self.mp == "fp16":
                            self.scaler.unscale_(self.optimizer)
                        nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip)
                    if self.mp == "fp16":
                        self.scaler.step(self.optimizer)
                        self.scaler.update()
                    else:
                        self.optimizer.step()
                    self.optimizer.zero_grad(set_to_none=True)
                    global_step += 1
                    if global_step % 100 == 0:
                        logger.info(
                            "Step %d | ORPO loss=%.4f | %s",
                            global_step,
                            loss.item(),
                            " | ".join(f"{k}={v:.4f}" for k, v in metrics.items()),
                        )
            avg_train = train_loss_sum / max(train_batches, 1)
            val_metrics = self._validate(val_loader) if val_loader is not None else {}
            log_msg = f"Epoch {epoch + 1}/{epochs} | ORPO Train loss: {avg_train:.4f}"
            if val_metrics:
                log_msg += f" | Val loss: {val_metrics['val_loss']:.4f}"
                if val_metrics["val_loss"] < best_loss:
                    best_loss = val_metrics["val_loss"]
                    self._save_checkpoint(output_dir, "orpo", epoch, best_loss)
            logger.info(log_msg)
        self._save_final(output_dir, "orpo")
        return {"best_loss": best_loss, "final_train_loss": avg_train}

    def _validate(self, val_loader: DataLoader) -> dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        batches = 0
        with torch.no_grad():
            for batch in val_loader:
                chosen_ids = batch["chosen_input_ids"].to(self.device, non_blocking=True)
                rejected_ids = batch["rejected_input_ids"].to(self.device, non_blocking=True)
                chosen_mask = batch["chosen_attention_mask"].to(self.device, non_blocking=True)
                rejected_mask = batch["rejected_attention_mask"].to(self.device, non_blocking=True)
                loss, _ = self._orpo_loss(chosen_ids, rejected_ids, chosen_mask, rejected_mask)
                total_loss += loss.item()
                batches += 1
        return {"val_loss": total_loss / max(batches, 1)}

    def _save_checkpoint(self, output_dir: str, method: str, epoch: int, loss: float) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_best.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {"epoch": epoch, "method": method, "best_loss": loss, "model_state_dict": unwrapped.state_dict(), "config": self.config},
            path,
        )
        logger.info("Saved best ORPO checkpoint to %s", path)

    def _save_final(self, output_dir: str, method: str) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_final.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {"method": method, "model_state_dict": unwrapped.state_dict(), "config": self.config},
            path,
        )
        logger.info("Saved final ORPO checkpoint to %s", path)
