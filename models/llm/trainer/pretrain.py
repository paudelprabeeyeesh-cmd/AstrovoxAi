import os
from typing import Optional
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm
from model.model import LLM
from tokenizer.train_tokenizer import TextDataset, collate_fn, load_tokenizer
from utils.helpers import load_config, count_parameters, get_device, set_cpu_threads, ValidationSplit
from trainer.checkpoint import save_checkpoint, load_checkpoint, list_checkpoints, remove_old_checkpoints
from trainer.metrics import evaluate_metrics, compute_perplexity


def pretrain(config_path="configs/config_100m.yaml", resume_from: Optional[str] = None):
    config = load_config(config_path)
    device = get_device()
    if device == "cpu":
        set_cpu_threads(min(2, os.cpu_count() or 1))
    model = LLM(config).to(device)
    print(f"Parameters: {count_parameters(model):,}")

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}. Train it first.")
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    train_file = config.get("train_file", "data/train.txt")
    streaming = config.get("streaming", False)
    block_size = config.get("max_position_embeddings", 1024)
    if streaming:
        from training_data.prepare import PretrainDataset
        dataset = PretrainDataset(train_file, tokenizer, block_size=block_size, streaming=True)
    else:
        dataset = TextDataset(train_file, tokenizer, block_size=block_size)

    split = ValidationSplit(dataset, val_ratio=config.get("val_ratio", 0.05))
    train_dataset = split.train_dataset()
    val_dataset = split.val_dataset()

    batch_size = config.get("batch_size", 1)
    num_workers = 0 if device == "cpu" else min(2, os.cpu_count() or 1)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=(device == "cuda"),
        collate_fn=lambda b: collate_fn(b, pad_token_id),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=max(1, batch_size // 2),
        shuffle=False,
        num_workers=num_workers,
        pin_memory=(device == "cuda"),
        collate_fn=lambda b: collate_fn(b, pad_token_id),
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.get("lr", 3e-4), betas=(0.9, 0.95), weight_decay=0.1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=len(train_loader) * config.get("epochs", 1))
    use_cuda = device == "cuda"
    scaler = GradScaler(enabled=use_cuda)

    start_epoch = 0
    best_val_loss = float("inf")
    checkpoint_path = config.get("checkpoint_dir", "checkpoints")
    os.makedirs(checkpoint_path, exist_ok=True)
    latest_ckpt = os.path.join(checkpoint_path, "latest.pt")
    if resume_from and os.path.exists(resume_from):
        start_epoch, best_val_loss = load_checkpoint(model, optimizer, scheduler, resume_from, device=device)
        print(f"Resumed from {resume_from} at epoch {start_epoch}")
    elif os.path.exists(latest_ckpt):
        start_epoch, best_val_loss = load_checkpoint(model, optimizer, scheduler, latest_ckpt, device=device)
        print(f"Resumed from {latest_ckpt} at epoch {start_epoch}")

    accumulation_steps = config.get("gradient_accumulation_steps", 16)
    gradient_clip = config.get("gradient_clip_norm", 1.0)
    checkpoint_every = config.get("checkpoint_every", 500)
    eval_every = config.get("eval_every", 500)
    max_train_steps = config.get("max_train_steps", None)

    model.train()
    global_step = 0
    for epoch in range(start_epoch, config.get("epochs", 1)):
        total_loss = 0.0
        pbar = tqdm(train_loader, desc=f"Pretrain Epoch {epoch + 1}")
        for i, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            if use_cuda:
                with autocast():
                    outputs = model(input_ids, labels=labels, use_gradient_checkpointing=config.get("gradient_checkpointing", True))
                    loss = outputs["loss"] / accumulation_steps
                scaler.scale(loss).backward()
            else:
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=config.get("gradient_checkpointing", True))
                loss = outputs["loss"] / accumulation_steps
                loss.backward()
            total_loss += loss.item() * accumulation_steps

            if (i + 1) % accumulation_steps == 0:
                if gradient_clip > 0:
                    if use_cuda:
                        scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip)
                if use_cuda:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()
                global_step += 1

            pbar.set_postfix({"loss": f"{total_loss / (i + 1):.4f}"})

            if max_train_steps and global_step >= max_train_steps:
                break

            if (i + 1) % eval_every == 0 or (i + 1) == len(train_loader):
                metrics = evaluate_metrics(model, val_loader, device)
                val_loss = metrics["loss"]
                val_ppl = metrics["perplexity"]
                val_acc = metrics["accuracy"]
                print(f"Step {global_step} | Val loss: {val_loss:.4f} | Val ppl: {val_ppl:.2f} | Val acc: {val_acc:.4f}")
                model.train()
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss,
                                    os.path.join(checkpoint_path, f"best_epoch{epoch + 1}.pt"), config=config)

            if (i + 1) % checkpoint_every == 0:
                save_checkpoint(model, optimizer, scheduler, epoch, best_val_loss, latest_ckpt, config=config)
                remove_old_checkpoints(checkpoint_path, keep_last_n=3)

        save_checkpoint(model, optimizer, scheduler, epoch + 1, best_val_loss, latest_ckpt, config=config)
        remove_old_checkpoints(checkpoint_path, keep_last_n=3)

    output_path = config.get("output_dir", "model.pt")
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    torch.save(model.state_dict(), output_path)
    print(f"Model saved to {output_path}")

    if isinstance(dataset, PretrainDataset):
        dataset.close()


if __name__ == "__main__":
    pretrain()
