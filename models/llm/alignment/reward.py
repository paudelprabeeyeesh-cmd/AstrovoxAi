import json
import logging
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

logger = logging.getLogger(__name__)


def preference_collate_fn(
    batch: list[dict[str, Any]],
    pad_token_id: int = 0,
    max_length: int = 2048,
) -> dict[str, torch.Tensor]:
    max_len = min(
        max(
            max(len(item["chosen_input_ids"]) for item in batch),
            max(len(item["rejected_input_ids"]) for item in batch),
        ),
        max_length,
    )
    B = len(batch)
    chosen_input_ids = torch.zeros(B, max_len, dtype=torch.long)
    rejected_input_ids = torch.zeros(B, max_len, dtype=torch.long)
    chosen_attention_mask = torch.zeros(B, max_len, dtype=torch.long)
    rejected_attention_mask = torch.zeros(B, max_len, dtype=torch.long)
    for i, item in enumerate(batch):
        c_ids = item["chosen_input_ids"][:max_len]
        r_ids = item["rejected_input_ids"][:max_len]
        chosen_input_ids[i, :len(c_ids)] = torch.tensor(c_ids, dtype=torch.long)
        rejected_input_ids[i, :len(r_ids)] = torch.tensor(r_ids, dtype=torch.long)
        chosen_attention_mask[i, :len(c_ids)] = 1
        rejected_attention_mask[i, :len(r_ids)] = 1
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
        self.samples: list[dict[str, Any]] = []
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Preference dataset not found: {data_path}")
        with open(data_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    self.samples.append(record)
                except json.JSONDecodeError as exc:
                    logger.warning("Skipping malformed preference line: %s", exc)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
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
        attention_mask: torch.Tensor | None = None,
        use_gradient_checkpointing: bool = False,
    ) -> dict[str, torch.Tensor]:
        outputs = self.llm(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_gradient_checkpointing=use_gradient_checkpointing,
        )
        hidden_states = outputs["logits"]
        last_token_idx = (
            attention_mask.sum(dim=1) - 1 if attention_mask is not None else input_ids.size(1) - 1
        )
        last_token_idx = (
            last_token_idx.clamp(min=0).unsqueeze(1).unsqueeze(2).expand(-1, 1, self.hidden_size)
        )
        last_hidden = hidden_states.gather(1, last_token_idx).squeeze(1)
        reward = self.reward_head(last_hidden).squeeze(-1)
        return {"reward": reward, "logits": hidden_states}


def compute_reward_loss(
    chosen_reward: torch.Tensor,
    rejected_reward: torch.Tensor,
    margin: float = 0.5,
) -> torch.Tensor:
    return -F.logsigmoid(chosen_reward - rejected_reward - margin).mean()


def compute_pairwise_accuracy(
    chosen_reward: torch.Tensor,
    rejected_reward: torch.Tensor,
) -> float:
    correct = (chosen_reward > rejected_reward).sum().item()
    total = chosen_reward.numel()
    return correct / max(total, 1)


class RewardTrainer:
    def __init__(
        self,
        model: nn.Module,
        tokenizer,
        config: dict[str, Any],
        train_dataset: PreferenceDataset | None = None,
        val_dataset: PreferenceDataset | None = None,
    ):
        if not isinstance(model, RewardModel):
            raise TypeError("RewardTrainer requires a RewardModel instance.")
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
        self.model.to(self.device)
        self.margin = float(config.get("reward_margin", 0.5))
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=float(config.get("reward_lr", 5e-5)), weight_decay=float(config.get("weight_decay", 0.01))
        )
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))

    def _autocast_context(self):
        if self.mp == "bf16":
            return autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True)
        if self.mp == "fp16":
            return autocast(device_type="cuda", enabled=True)
        return autocast(device_type="cpu", dtype=torch.float32, enabled=False)

    def train(self, output_dir: str, epochs: int | None = None) -> dict[str, float]:
        epochs = epochs if epochs is not None else int(self.config.get("reward_epochs", 1))
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
                with self._autocast_context():
                    chosen_outputs = self.model(
                        chosen_ids, attention_mask=chosen_mask, use_gradient_checkpointing=True
                    )
                    rejected_outputs = self.model(
                        rejected_ids, attention_mask=rejected_mask, use_gradient_checkpointing=True
                    )
                    chosen_reward = chosen_outputs["reward"]
                    rejected_reward = rejected_outputs["reward"]
                    loss = compute_reward_loss(chosen_reward, rejected_reward, margin=self.margin) / accumulation
                if self.mp == "fp16":
                    self.scaler.scale(loss).backward()
                else:
                    loss.backward()
                train_loss_sum += loss.item() * accumulation
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
            avg_train = train_loss_sum / max(train_batches, 1)
            val_metrics = self._validate(val_loader) if val_loader is not None else {}
            log_msg = f"Epoch {epoch + 1}/{epochs} | Reward Train loss: {avg_train:.4f}"
            if val_metrics:
                log_msg += f" | Val loss: {val_metrics['val_loss']:.4f}"
                val_loss_val = val_metrics["val_loss"]
                if val_loss_val < best_loss:
                    best_loss = val_loss_val
                    self._save_checkpoint(output_dir, "reward", epoch, best_loss)
            logger.info(log_msg)
        self._save_final(output_dir, "reward")
        return {"best_loss": best_loss, "final_train_loss": avg_train}

    def _validate(self, val_loader: DataLoader) -> dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        total_acc = 0.0
        batches = 0
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
                    loss = compute_reward_loss(chosen_reward, rejected_reward, margin=self.margin)
                    acc = compute_pairwise_accuracy(chosen_reward, rejected_reward)
                total_loss += loss.item()
                total_acc += acc
                batches += 1
        return {"val_loss": total_loss / max(batches, 1), "val_accuracy": total_acc / max(batches, 1)}

    def _save_checkpoint(self, output_dir: str, method: str, epoch: int, loss: float) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_best.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {"epoch": epoch, "method": method, "best_loss": loss, "model_state_dict": unwrapped.state_dict(), "config": self.config},
            path,
        )
        logger.info("Saved best reward checkpoint to %s", path)

    def _save_final(self, output_dir: str, method: str) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_final.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {"method": method, "model_state_dict": unwrapped.state_dict(), "config": self.config},
            path,
        )
        logger.info("Saved final reward checkpoint to %s", path)
