import os
import sys
import yaml
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast

from ..model.model import LLM
from ..tokenizer.train_tokenizer import TextDataset, collate_fn, load_tokenizer
from ..utils.helpers import load_config, count_parameters, get_device, set_cpu_threads, ValidationSplit


def get_8bit_optimizer(model, lr=3e-4):
    try:
        import bitsandbytes as bnb
        optimizer = bnb.optim.AdamW8bit(model.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
        return optimizer
    except Exception:
        return torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)


def train(config_path="configs/config_100m.yaml"):
    config = load_config(config_path)
    device = get_device()
    model = LLM(config).to(device)
    print(f"Parameters: {count_parameters(model):,}")

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}. Train it first.")

    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    dataset = TextDataset(config["train_file"], tokenizer, block_size=config.get("max_position_embeddings", 1024))
    dataloader = DataLoader(dataset, batch_size=config["batch_size"], shuffle=True,
                            num_workers=0, pin_memory=(device == "cuda"), collate_fn=lambda b: collate_fn(b, pad_token_id))

    optimizer = get_8bit_optimizer(model, lr=config.get("lr", 3e-4))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=len(dataloader) * config.get("epochs", 1))
    scaler = GradScaler(enabled=(device == "cuda"))

    model.train()
    accumulation_steps = config.get("gradient_accumulation_steps", 1)
    for epoch in range(config.get("epochs", 1)):
        total_loss = 0.0
        for i, batch in enumerate(dataloader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            with autocast(enabled=(device == "cuda")):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=config.get("gradient_checkpointing", False))
                loss = outputs["loss"] / accumulation_steps
            scaler.scale(loss).backward()
            if (i + 1) % accumulation_steps == 0:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()
            total_loss += loss.item() * accumulation_steps
        print(f"Epoch {epoch + 1}, Loss: {total_loss / len(dataloader):.4f}")

    save_path = config.get("output_dir", "model.pt")
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")


if __name__ == "__main__":
    train()
