import copy
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


def instruction_collate_fn(
    batch: list[dict[str, Any]],
    pad_token_id: int = 0,
    max_length: int = 2048,
) -> dict[str, torch.Tensor]:
    max_len = min(max(len(item["input_ids"]) for item in batch), max_length)
    input_ids = torch.zeros(len(batch), max_len, dtype=torch.long)
    labels = torch.full((len(batch), max_len), -100, dtype=torch.long)
    attention_mask = torch.zeros(len(batch), max_len, dtype=torch.long)
    for i, item in enumerate(batch):
        seq = item["input_ids"][:max_len]
        input_ids[i, :len(seq)] = torch.tensor(seq, dtype=torch.long)
        attention_mask[i, :len(seq)] = 1
        seq_labels = item.get("labels", seq[:])
        if len(seq_labels) > max_len:
            seq_labels = seq_labels[:max_len]
        labels[i, :len(seq_labels)] = torch.tensor(seq_labels, dtype=torch.long)
    return {"input_ids": input_ids, "labels": labels, "attention_mask": attention_mask}


class InstructionDataset(Dataset):
    def __init__(
        self,
        path: str,
        tokenizer,
        block_size: int = 2048,
        system_prompt: str = "You are a helpful assistant.",
    ):
        self.path = path
        self.tokenizer = tokenizer
        self.block_size = block_size
        self.system_prompt = system_prompt
        self.examples: list[dict[str, Any]] = []
        self._load()

    def _format_example(
        self, instruction: str, input_text: str = "", output_text: str = ""
    ) -> str:
        if input_text:
            prompt = (
                f"<s>[INST] {self.system_prompt}\n\n{instruction}\n\n{input_text} [/INST]"
            )
        else:
            prompt = f"<s>[INST] {self.system_prompt}\n\n{instruction} [/INST]"
        response = f" {output_text}</s>"
        return prompt + response

    def _load(self) -> None:
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                except json.JSONDecodeError:
                    continue
                instruction = sample.get("instruction", "")
                input_text = sample.get("input", "")
                output_text = sample.get("output", "")
                if not instruction or not output_text:
                    continue
                text = self._format_example(instruction, input_text, output_text)
                tokenized = self.tokenizer.encode(text).ids
                labels = tokenized[1:] + [-100]
                for start in range(0, max(len(tokenized) - self.block_size, 0), self.block_size):
                    chunk = tokenized[start: start + self.block_size]
                    chunk_labels = labels[start: start + self.block_size]
                    if len(chunk) > 0:
                        self.examples.append({"input_ids": chunk, "labels": chunk_labels})

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.examples[idx]


def compute_instruction_loss(
    logits: torch.Tensor, labels: torch.Tensor, ignore_index: int = -100
) -> torch.Tensor:
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    return F.cross_entropy(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1),
        ignore_index=ignore_index,
    )


class SFTTrainer:
    def __init__(
        self,
        model: nn.Module,
        tokenizer,
        config: dict[str, Any],
        train_dataset: InstructionDataset | None = None,
        val_dataset: InstructionDataset | None = None,
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
        self.model.to(self.device)
        lr = float(config.get("sft_lr", config.get("lr", 5e-5)))
        weight_decay = float(config.get("weight_decay", 0.01))
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))

    def _autocast_context(self):
        if self.mp == "bf16":
            return autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True)
        if self.mp == "fp16":
            return autocast(device_type="cuda", enabled=True)
        return autocast(device_type="cpu", dtype=torch.float32, enabled=False)

    def train(
        self, output_dir: str, epochs: int | None = None
    ) -> dict[str, float]:
        epochs = epochs if epochs is not None else int(self.config.get("sft_epochs", 3))
        batch_size = int(self.config.get("sft_batch_size", self.config.get("batch_size", 2)))
        grad_clip = float(self.config.get("gradient_clip_norm", 1.0))
        accumulation = int(self.config.get("gradient_accumulation_steps", 1))
        pad_token_id = self.tokenizer.token_to_id("<pad>") or 0
        max_length = int(self.config.get("max_position_embeddings", self.config.get("max_length", 2048)))

        train_loader = DataLoader(
            self.train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            collate_fn=lambda b: instruction_collate_fn(b, pad_token_id=pad_token_id, max_length=max_length),
            drop_last=True,
        )
        val_loader = None
        if self.val_dataset is not None and len(self.val_dataset) > 0:
            val_loader = DataLoader(
                self.val_dataset,
                batch_size=max(1, batch_size // 2),
                shuffle=False,
                num_workers=0,
                collate_fn=lambda b: instruction_collate_fn(b, pad_token_id=pad_token_id, max_length=max_length),
                drop_last=False,
            )
        best_val_loss = float("inf")
        global_step = 0
        for epoch in range(epochs):
            self.model.train()
            train_loss_sum = 0.0
            train_batches = 0
            for batch in train_loader:
                input_ids = batch["input_ids"].to(self.device, non_blocking=True)
                labels = batch["labels"].to(self.device, non_blocking=True)
                with self._autocast_context():
                    outputs = self.model(
                        input_ids, labels=labels, use_gradient_checkpointing=True
                    )
                    loss = outputs["loss"] / accumulation
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
            val_loss = self._validate(val_loader) if val_loader is not None else None
            log_msg = f"Epoch {epoch + 1}/{epochs} | SFT Train loss: {avg_train:.4f}"
            if val_loss is not None:
                log_msg += f" | Val loss: {val_loss:.4f}"
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self._save_checkpoint(output_dir, "sft", epoch, best_val_loss)
            logger.info(log_msg)
        self._save_final(output_dir, "sft")
        return {"best_val_loss": best_val_loss, "final_train_loss": avg_train}

    def _validate(self, val_loader: DataLoader) -> float:
        self.model.eval()
        total_loss = 0.0
        batches = 0
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(self.device, non_blocking=True)
                labels = batch["labels"].to(self.device, non_blocking=True)
                with self._autocast_context():
                    outputs = self.model(input_ids, labels=labels)
                    loss = outputs["loss"]
                total_loss += loss.item()
                batches += 1
        return total_loss / max(batches, 1)

    def _save_checkpoint(self, output_dir: str, method: str, epoch: int, loss: float) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_best.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {"epoch": epoch, "method": method, "best_loss": loss, "model_state_dict": unwrapped.state_dict(), "config": self.config},
            path,
        )
        logger.info("Saved best SFT checkpoint to %s", path)

    def _save_final(self, output_dir: str, method: str) -> None:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{method}_final.pt")
        unwrapped = self.model.module if hasattr(self.model, "module") else self.model
        torch.save(
            {"method": method, "model_state_dict": unwrapped.state_dict(), "config": self.config},
            path,
        )
        logger.info("Saved final SFT checkpoint to %s", path)
