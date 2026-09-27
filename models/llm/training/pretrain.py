import contextlib
import logging
import math
import os

import torch
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import get_device, load_config, set_cpu_threads

logger = logging.getLogger(__name__)


def _build_model(config, device, dtype):
    return LLM(config, device=torch.device(device), dtype=dtype)


def _create_optimizer(model, config):
    name = config.get("optimizer", "adamw").lower()
    lr = config.get("lr", 3e-4)
    wd = config.get("weight_decay", 0.1)
    if name == "adafactor":
        return torch.optim.AdaFactor(model.parameters(), lr=lr, weight_decay=wd)
    return torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd, betas=(0.9, 0.95))


def _create_scheduler(optimizer, config, dataloader_len):
    name = config.get("lr_scheduler", "cosine").lower()
    epochs = config.get("epochs", 1)
    warmup = config.get("warmup_steps", int(dataloader_len * epochs * 0.01))
    if name == "cosine":
        return torch.optim.lr_scheduler.SequentialLR(
            optimizer,
            schedulers=[
                torch.optim.lr_scheduler.LinearLR(
                    optimizer, start_factor=0.1, end_factor=1.0, total_iters=warmup
                ),
                torch.optim.lr_scheduler.CosineAnnealingLR(
                    optimizer,
                    T_max=dataloader_len * epochs - warmup,
                    eta_min=config.get("min_lr", 1e-6),
                ),
            ],
            milestones=[warmup],
        )
    if name == "linear":
        return torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=1.0, end_factor=0.0, total_iters=dataloader_len * epochs
        )
    return torch.optim.lr_scheduler.ConstantLR(optimizer, factor=1.0)


def train(config_path="models/llm/configs/config_4b.yaml", resume_from=None):
    from ..training_data.pipeline import StreamingDataset

    config = load_config(config_path)
    device = get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))
    torch.manual_seed(config.get("seed", 42))
    torch.cuda.manual_seed_all(config.get("seed", 42))
    mp = config.get("mixed_precision", "none")
    dtype = torch.float32
    if mp == "bf16" and hasattr(torch, "bfloat16"):
        dtype = torch.bfloat16
    elif mp == "fp16" and device == "cuda":
        dtype = torch.float16
    model = _build_model(config, device, dtype)
    tokenizer = load_tokenizer(config.get("tokenizer_path", "tokenizer.json"))
    train_file = config.get("train_file", "data/train.txt")
    train_dataset = StreamingDataset(
        train_file,
        tokenizer,
        block_size=config.get("max_position_embeddings", 2048),
        streaming=True,
    )
    val_dataset = StreamingDataset(
        config.get("val_file", train_file),
        tokenizer,
        block_size=config.get("max_position_embeddings", 2048),
        streaming=True,
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.get("batch_size", 1),
        shuffle=True,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=max(1, config.get("batch_size", 1) // 2),
        shuffle=False,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0),
        drop_last=False,
    )
    optimizer = _create_optimizer(model, config)
    scheduler = _create_scheduler(optimizer, config, len(train_loader))
    scaler = GradScaler(enabled=(mp == "fp16" and device == "cuda"))
    start_epoch = 0
    best_val_loss = float("inf")
    if resume_from and os.path.exists(resume_from):
        start_epoch, best_val_loss = load_checkpoint(
            model, optimizer, scheduler, resume_from, device=device
        )
    accumulation = config.get("gradient_accumulation_steps", 1)
    grad_clip = config.get("gradient_clip_norm", 1.0)
    for epoch in range(start_epoch, config.get("epochs", 1)):
        train_metrics = train_epoch(
            model,
            train_loader,
            optimizer,
            scheduler,
            scaler,
            device,
            accumulation,
            grad_clip,
            mp,
            epoch,
        )
        val_metrics = validate(
            model, val_loader, device, max_batches=config.get("max_val_batches", None), mp=mp
        )
        logger.info(
            f"Epoch {epoch+1} | Train loss: {train_metrics['train_loss']:.4f} | Val loss: {val_metrics['loss']:.4f} | Val ppl: {val_metrics['perplexity']:.2f}"
        )
        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            save_checkpoint(
                model,
                optimizer,
                scheduler,
                epoch,
                best_val_loss,
                config.get("best_checkpoint", "best.pt"),
                config,
                global_step=epoch,
            )
    output_path = config.get("output_dir", "model.pt")
    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
    )
    torch.save(model.state_dict(), output_path)
    logger.info(f"Model saved to {output_path}")


def validate(model, dataloader, device, max_batches=None, mp="none"):
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    correct = 0
    for i, batch in enumerate(dataloader):
        if max_batches is not None and i >= max_batches:
            break
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)
        if mp == "bf16":
            with autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
        elif mp == "fp16":
            with autocast(device_type="cuda", enabled=True):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
        else:
            outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
        loss = outputs["loss"].item()
        logits = outputs["logits"]
        total_loss += loss * labels.numel()
        total_tokens += labels.numel()
        preds = logits.argmax(dim=-1)
        mask = labels != -100
        correct += (preds[mask] == labels[mask]).sum().item()
    avg_loss = total_loss / max(total_tokens, 1)
    accuracy = correct / max(total_tokens, 1)
    perplexity = math.exp(avg_loss) if avg_loss < 100 else float("inf")
    return {
        "loss": avg_loss,
        "perplexity": perplexity,
        "accuracy": accuracy,
        "tokens": total_tokens,
    }


def train_epoch(
    model,
    dataloader,
    optimizer,
    scheduler,
    scaler,
    device,
    accumulation_steps,
    grad_clip,
    mp,
    epoch,
    tracker=None,
):
    import time

    from tqdm import tqdm

    model.train()
    total_loss = 0.0
    tokens = 0
    grad_norm = 0.0
    start = time.time()
    pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}")
    for i, batch in enumerate(pbar):
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)
        if mp == "bf16":
            with autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=True)
                loss = outputs["loss"] / accumulation_steps
            loss.backward()
        elif mp == "fp16":
            with autocast(device_type="cuda", enabled=True):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=True)
                loss = outputs["loss"] / accumulation_steps
            scaler.scale(loss).backward()
        else:
            outputs = model(input_ids, labels=labels, use_gradient_checkpointing=True)
            loss = outputs["loss"] / accumulation_steps
            loss.backward()
        total_loss += loss.item() * accumulation_steps
        tokens += labels.numel()
        if (i + 1) % accumulation_steps == 0:
            if grad_clip > 0:
                if mp == "fp16":
                    scaler.unscale_(optimizer)
                total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                grad_norm = total_norm.item()
            if mp == "fp16":
                scaler.step(optimizer)
                scaler.update()
            else:
                optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            if scheduler:
                scheduler.step()
        elapsed = time.time() - start
        tokens_per_sec = tokens / max(elapsed, 1e-6)
        pbar.set_postfix({"loss": f"{total_loss / (i+1):.4f}", "tokens/s": f"{tokens_per_sec:.1f}"})
    return {
        "train_loss": total_loss / max(1, len(dataloader)),
        "tokens": tokens,
        "tokens_per_sec": tokens_per_sec,
        "grad_norm": grad_norm,
        "epoch_time": elapsed,
    }


def save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss, path, config, global_step):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    unwrapped = model.module if hasattr(model, "module") else model
    state = {
        "epoch": epoch,
        "global_step": global_step,
        "best_val_loss": best_val_loss,
        "model_state_dict": unwrapped.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": config,
    }
    if scheduler:
        state["scheduler_state_dict"] = scheduler.state_dict()
    torch.save(state, path)


def load_checkpoint(model, optimizer, scheduler, path, device):
    if not os.path.exists(path):
        return 0, float("inf")
    state = torch.load(path, map_location=device, weights_only=False)
    unwrapped = model.module if hasattr(model, "module") else model
    unwrapped.load_state_dict(state["model_state_dict"], strict=False)
    if "optimizer_state_dict" in state:
        optimizer.load_state_dict(state["optimizer_state_dict"])
    if scheduler is not None and "scheduler_state_dict" in state:
        with contextlib.suppress(Exception):
            scheduler.load_state_dict(state["scheduler_state_dict"])
    return state.get("epoch", 0), state.get("best_val_loss", float("inf"))


def collate_fn(batch, pad_token_id=0):
    max_len = max(item["input_ids"].size(0) for item in batch)
    input_ids = torch.zeros(len(batch), max_len, dtype=torch.long)
    labels = torch.full((len(batch), max_len), -100, dtype=torch.long)
    for i, item in enumerate(batch):
        length = item["input_ids"].size(0)
        input_ids[i, :length] = item["input_ids"]
        labels[i, :length] = item["labels"]
    return {"input_ids": input_ids, "labels": labels}


class PretrainPipeline:
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

    def run(self, resume_from: str | None = None):
        model = _build_model(self.config, self.device, self.dtype)
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        train_file = self.config.get("train_file", "data/train.txt")
        if not os.path.exists(train_file):
            raise FileNotFoundError(f"Training file not found: {train_file}")
        from ..training_data.pipeline import StreamingDataset

        train_dataset = StreamingDataset(
            train_file,
            tokenizer,
            block_size=self.config.get("max_position_embeddings", 2048),
            streaming=True,
        )
        val_dataset = StreamingDataset(
            self.config.get("val_file", train_file),
            tokenizer,
            block_size=self.config.get("max_position_embeddings", 2048),
            streaming=True,
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.get("batch_size", 1),
            shuffle=True,
            num_workers=0,
            collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0),
            drop_last=True,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=max(1, self.config.get("batch_size", 1) // 2),
            shuffle=False,
            num_workers=0,
            collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0),
            drop_last=False,
        )
        optimizer = _create_optimizer(model, self.config)
        scheduler = _create_scheduler(optimizer, self.config, len(train_loader))
        scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))
        start_epoch = 0
        best_val_loss = float("inf")
        if resume_from and os.path.exists(resume_from):
            start_epoch, best_val_loss = load_checkpoint(
                model, optimizer, scheduler, resume_from, device=self.device
            )
        accumulation = self.config.get("gradient_accumulation_steps", 1)
        grad_clip = self.config.get("gradient_clip_norm", 1.0)
        for epoch in range(start_epoch, self.config.get("epochs", 1)):
            train_metrics = train_epoch(
                model,
                train_loader,
                optimizer,
                scheduler,
                scaler,
                self.device,
                accumulation,
                grad_clip,
                self.mp,
                epoch,
            )
            val_metrics = validate(
                model,
                val_loader,
                self.device,
                max_batches=self.config.get("max_val_batches", None),
                mp=self.mp,
            )
            logger.info(
                f"Epoch {epoch+1} | Train loss: {train_metrics['train_loss']:.4f} | Val loss: {val_metrics['loss']:.4f} | Val ppl: {val_metrics['perplexity']:.2f}"
            )
            if val_metrics["loss"] < best_val_loss:
                best_val_loss = val_metrics["loss"]
                save_checkpoint(
                    model,
                    optimizer,
                    scheduler,
                    epoch,
                    best_val_loss,
                    self.config.get("best_checkpoint", "best.pt"),
                    self.config,
                    global_step=epoch,
                )
        output_path = self.config.get("output_dir", "model.pt")
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
        )
        torch.save(model.state_dict(), output_path)
        logger.info(f"Model saved to {output_path}")
        return {"best_val_loss": best_val_loss}
