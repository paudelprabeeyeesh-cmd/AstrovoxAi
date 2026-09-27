#!/usr/bin/env python3
"""
Train 1B parameter model end-to-end with meta-device streaming.
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.llm.model.model import LLM
from models.llm.utils.helpers import load_config, get_device, set_cpu_threads, count_parameters
from models.llm.tokenizer.train_tokenizer import (
    load_tokenizer,
    create_dummy_tokenizer,
    TextDataset,
    collate_fn,
)
from models.llm.trainer.checkpoint import save_checkpoint, load_checkpoint
from models.llm.inference.generate import generate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def create_synthetic_data(path: str, num_samples: int = 2000, block_size: int = 512):
    topics = [
        "The future of artificial intelligence is being shaped by transformer architectures and large-scale pretraining.",
        "Quantum computing promises exponential speedups for optimization, cryptography, and materials science.",
        "Robotics combines mechanical engineering, control theory, and computer vision to build autonomous systems.",
        "Climate models are becoming more accurate as resolution increases and physics constraints improve.",
        "Neuroscience reveals how plasticity, attention, and memory consolidation enable lifelong learning.",
        "Software engineering relies on modular design, testing, observability, and continuous integration.",
        "Mathematics provides the language for describing patterns in data, space, and computation.",
        "Space exploration expands humanity's reach through propulsion, navigation, and life-support systems.",
        "Biotechnology accelerates discovery with genome sequencing, protein folding, and lab automation.",
        "Renewable energy systems require grid-scale storage, forecasting, and demand response optimization.",
    ]
    with open(path, "w", encoding="utf-8") as f:
        for i in range(num_samples):
            text = " ".join(topics[i % len(topics)] for _ in range(3))
            text = (
                f"Sample {i}: "
                + text
                + " "
                + " ".join(topics[(i + 1) % len(topics)] for _ in range(2))
            )
            f.write(text + "\n")
    logger.info(f"Created synthetic dataset: {path} with {num_samples} samples")


def train_epoch(
    model, dataloader, optimizer, scheduler, device, accumulation_steps, grad_clip, epoch, dtype
):
    model.train()
    total_loss = 0.0
    tokens = 0
    grad_norm = 0.0
    start = time.time()
    from tqdm import tqdm

    pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}")
    for i, batch in enumerate(pbar):
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)
        if dtype == torch.bfloat16:
            with torch.cuda.amp.autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=True)
                loss = outputs["loss"] / accumulation_steps
            loss.backward()
        else:
            outputs = model(input_ids, labels=labels, use_gradient_checkpointing=True)
            loss = outputs["loss"] / accumulation_steps
            loss.backward()
        total_loss += loss.item() * accumulation_steps
        tokens += labels.numel()
        if (i + 1) % accumulation_steps == 0:
            if grad_clip > 0:
                total_norm = nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                grad_norm = total_norm.item()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            if scheduler:
                scheduler.step()
        elapsed = time.time() - start
        tokens_per_sec = tokens / max(elapsed, 1e-6)
        pbar.set_postfix(
            {
                "loss": f"{total_loss / (i+1):.4f}",
                "tokens/s": f"{tokens_per_sec:.1f}",
                "grad": f"{grad_norm:.2f}",
            }
        )
    return {
        "train_loss": total_loss / max(1, len(dataloader)),
        "tokens": tokens,
        "tokens_per_sec": tokens_per_sec,
        "grad_norm": grad_norm,
    }


@torch.no_grad()
def validate(model, dataloader, device, max_batches=None, dtype=torch.float32):
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    correct = 0
    for i, batch in enumerate(dataloader):
        if max_batches is not None and i >= max_batches:
            break
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)
        if dtype == torch.bfloat16:
            with torch.cuda.amp.autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
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
    perplexity = torch.exp(torch.tensor(avg_loss)).item() if avg_loss < 100 else float("inf")
    return {
        "loss": avg_loss,
        "perplexity": perplexity,
        "accuracy": accuracy,
        "tokens": total_tokens,
    }


def main(config_path="models/llm/configs/config_1b.yaml", resume_from=None):
    os.makedirs("logs", exist_ok=True)
    os.makedirs("checkpoints/1b", exist_ok=True)
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
    logger.info(f"Device: {device}, dtype: {dtype}")
    logger.info(f"Config: {config_path}")
    train_file = config.get("train_file", "data/train.txt")
    if not os.path.exists(train_file):
        create_synthetic_data(
            train_file, num_samples=2000, block_size=config.get("max_position_embeddings", 1024)
        )
    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        create_dummy_tokenizer(
            save_dir=os.path.dirname(tokenizer_path) or ".",
            vocab_size=config.get("vocab_size", 32000),
        )
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0
    dataset = TextDataset(
        train_file, tokenizer, block_size=config.get("max_position_embeddings", 1024)
    )
    n = len(dataset)
    g = torch.Generator().manual_seed(42)
    indices = torch.randperm(n, generator=g).tolist()
    split = int(n * 0.9)
    from torch.utils.data import Subset, DataLoader

    train_dataset = Subset(dataset, indices[:split])
    val_dataset = Subset(dataset, indices[split:])
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.get("batch_size", 1),
        shuffle=True,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=max(1, config.get("batch_size", 1) // 2),
        shuffle=False,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
        drop_last=False,
    )
    logger.info("Building 1B model...")
    build_start = time.time()
    try:
        model = LLM(config, device=torch.device(device), dtype=dtype)
    except RuntimeError as e:
        if "not enough memory" in str(e):
            logger.warning(
                "CPU memory insufficient; using meta init with reduced config for demonstration"
            )
            cfg = dict(config)
            cfg["hidden_size"] = min(cfg.get("hidden_size", 2048), 1536)
            cfg["num_hidden_layers"] = min(cfg.get("num_hidden_layers", 24), 18)
            cfg["intermediate_size"] = min(cfg.get("intermediate_size", 8192), 6144)
            config = cfg
            model = LLM(config, device=torch.device(device), dtype=dtype)
        else:
            raise
    build_time = time.time() - build_start
    params = count_parameters(model)
    logger.info(f"Model built in {build_time:.1f}s: {params:,} ({params/1e9:.2f}B) parameters")
    mem = model.estimate_memory(
        training=True, dtype_bytes=2 if dtype in (torch.float16, torch.bfloat16) else 4
    )
    logger.info(
        f"Estimated memory: weights={mem['weights_gb']:.1f}GB, total={mem['total_base_gb']:.1f}GB"
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.get("lr", 3e-4),
        betas=(0.9, 0.95),
        weight_decay=config.get("weight_decay", 0.1),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=len(train_loader) * config.get("epochs", 1)
    )
    start_epoch = 0
    if resume_from and os.path.exists(resume_from):
        start_epoch, _ = load_checkpoint(model, optimizer, scheduler, resume_from, device=device)
        logger.info(f"Resumed from {resume_from} at epoch {start_epoch}")
    accumulation_steps = config.get("gradient_accumulation_steps", 8)
    grad_clip = config.get("gradient_clip_norm", 1.0)
    checkpoint_dir = "checkpoints/1b"
    os.makedirs(checkpoint_dir, exist_ok=True)
    best_val_loss = float("inf")
    train_log = []
    val_log = []
    for epoch in range(start_epoch, config.get("epochs", 3)):
        logger.info(f"Starting epoch {epoch+1}/{config.get('epochs', 3)}")
        train_metrics = train_epoch(
            model,
            train_loader,
            optimizer,
            scheduler,
            device,
            accumulation_steps,
            grad_clip,
            epoch,
            dtype,
        )
        val_metrics = validate(
            model, val_loader, device, max_batches=config.get("max_val_batches"), dtype=dtype
        )
        train_log.append({"epoch": epoch + 1, **train_metrics})
        val_log.append({"epoch": epoch + 1, **val_metrics})
        logger.info(
            f"Epoch {epoch+1} | Train loss: {train_metrics['train_loss']:.4f} | Val loss: {val_metrics['loss']:.4f} | Val ppl: {val_metrics['perplexity']:.2f} | Tokens/s: {train_metrics['tokens_per_sec']:.1f}"
        )
        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            save_checkpoint(
                model,
                optimizer,
                scheduler,
                epoch,
                best_val_loss,
                os.path.join(checkpoint_dir, "best.pt"),
                config,
                global_step=epoch * len(train_loader),
            )
        save_checkpoint(
            model,
            optimizer,
            scheduler,
            epoch,
            val_metrics["loss"],
            os.path.join(checkpoint_dir, "latest.pt"),
            config,
            global_step=epoch * len(train_loader),
        )
    with open("logs/1b_training_log.json", "w") as f:
        json.dump(
            {
                "train": train_log,
                "val": val_log,
                "best_val_loss": best_val_loss,
                "params": params,
                "build_time_s": build_time,
            },
            f,
            indent=2,
        )
    logger.info("Generating samples...")
    samples = []
    prompts = [
        "Artificial intelligence will",
        "The best way to learn is",
        "In the future, we will",
        "Science has shown that",
        "Programming is powerful because",
    ]
    for p in prompts:
        try:
            out = generate(
                model, tokenizer, p, max_new_tokens=60, temperature=0.8, top_k=40, device=device
            )
            samples.append({"prompt": p, "generation": out})
            logger.info(f"Prompt: {p}\nGen: {out}\n")
        except Exception as e:
            logger.error(f"Generation error: {e}")
    with open("logs/1b_samples.json", "w") as f:
        json.dump(samples, f, indent=2)
    logger.info("1B training complete!")
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Training log: logs/1b_training_log.json")
    logger.info(f"Samples: logs/1b_samples.json")
    return {
        "best_val_loss": best_val_loss,
        "params": params,
        "train_log": train_log,
        "val_log": val_log,
        "samples": samples,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train 1B LLM")
    parser.add_argument("--config", default="models/llm/configs/config_1b.yaml")
    parser.add_argument("--resume", default=None)
    args = parser.parse_args()
    main(config_path=args.config, resume_from=args.resume)
