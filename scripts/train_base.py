import argparse
import csv
import math
import os
import random
import time
from pathlib import Path

import torch

from models.llm.inference.generate import generate
from models.llm.model.model import LLM
from models.llm.tokenizer.train_tokenizer import (
    TextDataset,
    collate_fn,
    create_dummy_tokenizer,
    load_tokenizer,
)
from models.llm.trainer.checkpoint import load_checkpoint, save_checkpoint
from models.llm.utils.helpers import get_device, load_config, set_cpu_threads


def ensure_determinism(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)


def create_synthetic_data(path: str, num_samples: int = 800, block_size: int = 128):
    sentences = [
        "Astrovox is an artificial intelligence platform designed for learning.",
        "The Astrovox model uses transformers to process text sequences.",
        "Training helps the model understand language patterns and structure.",
        "The model generates text based on learned patterns from data.",
        "Phase one focuses on basic pretraining with synthetic text.",
        "Synthetic data is used for quick testing and verification.",
        "The quick brown fox jumps over the lazy dog every day.",
        "Natural language processing enables computers to understand text.",
        "Deep learning models require careful tuning and validation.",
        "Gradient descent optimizes model parameters during training.",
        "Loss functions measure prediction errors in model outputs.",
        "Backpropagation updates neural network weights efficiently.",
        "Transformers use attention mechanisms to process sequences.",
        "Tokenization converts raw text into numerical token ids.",
        "Embeddings represent words as dense continuous vectors.",
        "Position encodings add sequence order information to embeddings.",
        "Feed forward networks process hidden states between layers.",
        "Layer normalization stabilizes training dynamics and speed.",
        "Dropout prevents overfitting by randomly zeroing activations.",
        "Learning rates control optimization step sizes carefully.",
        "Checkpoints save model state for later resumption.",
        "Validation loss indicates how well the model generalizes.",
        "Perplexity measures model uncertainty on held out data.",
        "Gradient clipping prevents exploding gradients during training.",
        "Mixed precision training reduces memory usage significantly.",
        "Batch size determines how many samples are processed together.",
        "Epochs count how many times the dataset is traversed fully.",
        "Tokens per second measures training throughput on hardware.",
        "AdamW optimizer decouples weight decay from gradient updates.",
        "Cosine annealing reduces learning rate over training steps.",
    ]
    text_blocks = []
    for i in range(num_samples):
        s = sentences[i % len(sentences)]
        text_blocks.append(s)
    full_text = "\n".join(text_blocks)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"Created synthetic data at {path} with {num_samples} samples")


def compute_grad_norm(model):
    total_norm = 0.0
    for p in model.parameters():
        if p.grad is not None:
            total_norm += p.grad.data.norm(2).item() ** 2
    return math.sqrt(total_norm)


def train_epoch(
    model,
    dataloader,
    optimizer,
    scheduler,
    device,
    accumulation_steps,
    grad_clip,
    epoch,
    log_rows,
    sample_rows,
    checkpoint_dir,
    step_offset,
    checkpoint_every,
    tokenizer,
    prompts,
):
    model.train()
    total_loss = 0.0
    total_tokens = 0
    nan_encountered = False
    start = time.time()
    step = step_offset

    for i, batch in enumerate(dataloader):
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)

        outputs = model(input_ids, labels=labels, use_gradient_checkpointing=True)
        loss = outputs["loss"] / accumulation_steps

        if torch.isnan(loss) or torch.isinf(loss):
            print(f"[stop] NaN/Inf loss at epoch {epoch+1} step {i+1}")
            nan_encountered = True
            break

        loss.backward()

        if (i + 1) % accumulation_steps == 0:
            grad_norm = compute_grad_norm(model)
            if math.isnan(grad_norm) or math.isinf(grad_norm) or grad_norm > 1e6:
                print(
                    f"[stop] Exploding gradients at epoch {epoch+1} step {i+1}: grad_norm={grad_norm:.4e}"
                )
                nan_encountered = True
                break

            if grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)

            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            if scheduler is not None:
                scheduler.step()
            step += 1

            train_loss = loss.item() * accumulation_steps
            total_loss += train_loss
            total_tokens += labels.numel()

            elapsed = time.time() - start
            tps = total_tokens / max(elapsed, 1e-6)
            current_lr = optimizer.param_groups[0]["lr"]
            ppl = math.exp(min(train_loss, 80))

            log_rows.append(
                {
                    "step": step,
                    "epoch": epoch + 1,
                    "train_loss": train_loss,
                    "val_loss": "",
                    "val_ppl": "",
                    "tokens_per_sec": tps,
                    "grad_norm": grad_norm,
                    "lr": current_lr,
                }
            )

            if step % checkpoint_every == 0:
                ckpt_path = os.path.join(checkpoint_dir, f"ckpt_step_{step}.pt")
                save_checkpoint(
                    model,
                    optimizer,
                    scheduler,
                    epoch,
                    float("inf"),
                    ckpt_path,
                    config=None,
                    global_step=step,
                )
                print(
                    f"[ckpt] step={step} loss={train_loss:.4f} ppl={ppl:.2f} tps={tps:.1f} grad_norm={grad_norm:.4e}"
                )

                samples = []
                for p in prompts:
                    try:
                        out = generate(
                            model,
                            tokenizer,
                            p,
                            max_new_tokens=40,
                            temperature=0.8,
                            top_k=40,
                            device=device,
                        )
                        samples.append(out.replace("\n", " ").strip())
                    except Exception as e:
                        samples.append(f"[gen_error] {e}")
                for s in samples:
                    sample_rows.append({"step": step, "text": s})
                    print(f"[sample] {s[:120]}")

    return nan_encountered, step


@torch.no_grad()
def validate(model, dataloader, device):
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    correct = 0
    for batch in dataloader:
        input_ids = batch["input_ids"].to(device, non_blocking=True)
        labels = batch["labels"].to(device, non_blocking=True)
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
    try:
        ppl = math.exp(min(avg_loss, 80))
    except OverflowError:
        ppl = float("inf")
    return avg_loss, ppl, accuracy


def run_training(config_path="models/llm/configs/config_100m.yaml", resume_from=None):
    ensure_determinism(seed=42)
    config = load_config(config_path)
    device = get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    dtype = torch.float32
    mp = config.get("mixed_precision", "none")
    if mp == "bf16" and hasattr(torch, "bfloat16"):
        dtype = torch.bfloat16
    elif mp == "fp16" and device == "cuda":
        dtype = torch.float16

    output_dir = config.get("output_dir", "model.pt")
    checkpoint_dir = os.path.join(
        os.path.dirname(output_dir) if os.path.dirname(output_dir) else ".", "phase1_checkpoints"
    )
    log_dir = os.path.join(
        os.path.dirname(output_dir) if os.path.dirname(output_dir) else ".", "phase1_logs"
    )
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    train_file = config.get("train_file", "data/train.txt")
    block_size = config.get("max_position_embeddings", 1024)
    if not os.path.exists(train_file):
        create_synthetic_data(train_file, num_samples=600, block_size=block_size)

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        create_dummy_tokenizer(
            save_dir=os.path.dirname(tokenizer_path) or ".",
            vocab_size=config.get("vocab_size", 32000),
        )
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    dataset = TextDataset(train_file, tokenizer, block_size=block_size)
    n = len(dataset)
    g = torch.Generator().manual_seed(42)
    indices = torch.randperm(n, generator=g).tolist()
    split = int(n * 0.9)
    from torch.utils.data import DataLoader, Subset

    train_dataset = Subset(dataset, indices[:split])
    val_dataset = Subset(dataset, indices[split:])
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.get("batch_size", 2),
        shuffle=True,
        num_workers=0,
        pin_memory=(device == "cuda"),
        collate_fn=lambda b: collate_fn(b, pad_token_id),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=max(1, config.get("batch_size", 2) // 2),
        shuffle=False,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
        drop_last=False,
    )

    model = LLM(config, device=torch.device(device), dtype=dtype)
    print(f"Parameters: {model.get_num_params():,}")

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.get("lr", 3e-4), betas=(0.9, 0.95), weight_decay=0.1
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=len(train_loader) * config.get("epochs", 1)
    )

    start_epoch = 0
    global_step = 0
    if resume_from and os.path.exists(resume_from):
        start_epoch, _ = load_checkpoint(model, optimizer, scheduler, resume_from, device=device)
        try:
            global_step = int(Path(resume_from).stem.split("_")[-1])
        except Exception:
            global_step = 0
        print(f"Resumed from {resume_from} at epoch {start_epoch} step {global_step}")

    accumulation_steps = config.get("gradient_accumulation_steps", 16)
    grad_clip = config.get("gradient_clip_norm", 1.0)
    checkpoint_every = config.get("checkpoint_every_steps", 50)
    epochs = config.get("epochs", 2)

    train_csv = os.path.join(log_dir, "training_metrics.csv")
    val_csv = os.path.join(log_dir, "validation_metrics.csv")
    sample_csv = os.path.join(log_dir, "samples.csv")
    tb_csv = os.path.join(log_dir, "tensorboard_metrics.csv")

    train_fields = [
        "step",
        "epoch",
        "train_loss",
        "val_loss",
        "val_ppl",
        "tokens_per_sec",
        "grad_norm",
        "lr",
    ]
    val_fields = ["step", "epoch", "val_loss", "val_ppl", "val_accuracy"]
    sample_fields = ["step", "text"]
    tb_fields = [
        "step",
        "epoch",
        "train_loss",
        "val_loss",
        "val_ppl",
        "tokens_per_sec",
        "grad_norm",
        "lr",
    ]

    train_rows = []
    val_rows = []
    sample_rows = []
    tb_rows = []

    best_val_loss = float("inf")
    prompts = [
        "Astrovox is",
        "The model learns",
        "Phase one focuses on",
        "Transformers use attention",
        "Gradient descent optimizes",
    ]

    initial_loss = None
    final_loss = None

    for epoch in range(start_epoch, epochs):
        log_rows = train_rows
        sample_rows_epoch = sample_rows
        nan_stop, global_step = train_epoch(
            model,
            train_loader,
            optimizer,
            scheduler,
            device,
            accumulation_steps,
            grad_clip,
            epoch,
            log_rows,
            sample_rows_epoch,
            checkpoint_dir,
            global_step,
            checkpoint_every,
            tokenizer,
            prompts,
        )
        if nan_stop:
            break

        val_loss, val_ppl, val_acc = validate(model, val_loader, device)
        val_rows.append(
            {
                "step": global_step,
                "epoch": epoch + 1,
                "val_loss": val_loss,
                "val_ppl": val_ppl,
                "val_accuracy": val_acc,
            }
        )
        print(
            f"Epoch {epoch+1} | Val loss: {val_loss:.4f} | Val ppl: {val_ppl:.2f} | Val acc: {val_acc:.4f}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_path = os.path.join(checkpoint_dir, "best.pt")
            save_checkpoint(
                model,
                optimizer,
                scheduler,
                epoch,
                best_val_loss,
                best_path,
                config=None,
                global_step=global_step,
            )

        latest = os.path.join(checkpoint_dir, "latest.pt")
        save_checkpoint(
            model,
            optimizer,
            scheduler,
            epoch,
            best_val_loss,
            latest,
            config=None,
            global_step=global_step,
        )

        for r in val_rows[-1:]:
            tb_rows.append(
                {
                    "step": r["step"],
                    "epoch": r["epoch"],
                    "train_loss": "",
                    "val_loss": r["val_loss"],
                    "val_ppl": r["val_ppl"],
                    "tokens_per_sec": "",
                    "grad_norm": "",
                    "lr": optimizer.param_groups[0]["lr"],
                }
            )

    with open(train_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=train_fields)
        writer.writeheader()
        writer.writerows(train_rows)
    with open(val_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=val_fields)
        writer.writeheader()
        writer.writerows(val_rows)
    with open(sample_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sample_fields)
        writer.writeheader()
        writer.writerows(sample_rows)
    with open(tb_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tb_fields)
        writer.writeheader()
        writer.writerows(tb_rows)

    print(f"Logs written to {log_dir}")
    print(f"Checkpoints written to {checkpoint_dir}")

    if train_rows:
        initial_loss = train_rows[0]["train_loss"]
        final_loss = train_rows[-1]["train_loss"]
        print(f"Initial train loss: {initial_loss:.4f}")
        print(f"Final train loss:   {final_loss:.4f}")
        if final_loss < initial_loss:
            print("Convergence check: PASSED (final loss < initial loss)")
        else:
            print("Convergence check: FAILED (final loss >= initial loss)")

    if val_rows:
        print(f"Best validation loss: {best_val_loss:.4f}")
        if len(val_rows) > 1 and val_rows[-1]["val_loss"] <= val_rows[0]["val_loss"]:
            print("Validation decreasing check: PASSED")
        else:
            print("Validation decreasing check: FAILED")

    final_path = config.get("output_dir", "model.pt")
    os.makedirs(os.path.dirname(final_path) if os.path.dirname(final_path) else ".", exist_ok=True)
    torch.save(model.state_dict(), final_path)
    print(f"Final model saved to {final_path}")

    return {
        "config_path": config_path,
        "best_val_loss": best_val_loss,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "train_rows": train_rows,
        "val_rows": val_rows,
        "sample_rows": sample_rows,
        "log_dir": log_dir,
        "checkpoint_dir": checkpoint_dir,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1 training harness")
    parser.add_argument("--config", default="models/llm/configs/config_phase1.yaml")
    parser.add_argument("--resume", default=None)
    args = parser.parse_args()
    run_training(config_path=args.config, resume_from=args.resume)
