import os
import math
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from model.model import LLM
from model.model_scaling import count_parameters, memory_estimation, chinchilla_optimal_tokens
from tokenizer.train_tokenizer import TextDataset, collate_fn, load_tokenizer
from utils.helpers import load_config, get_device
from trainer.checkpoint import save_checkpoint, load_checkpoint
from trainer.metrics import compute_perplexity, validate


def pretrain(config_path="configs/config_40b.yaml"):
    config = load_config(config_path)
    device = get_device()
    hidden_size = config["hidden_size"]
    vocab_size = config["vocab_size"]
    num_hidden_layers = config["num_hidden_layers"]
    num_attention_heads = config["num_attention_heads"]
    intermediate_size = config["intermediate_size"]
    max_position_embeddings = config.get("max_position_embeddings", 2048)

    num_params = count_parameters(
        hidden_size, vocab_size, num_hidden_layers, num_attention_heads,
        intermediate_size, max_position_embeddings
    )
    print(f"Estimated parameters: {num_params:,}")
    mem = memory_estimation(num_params)
    print(f"Estimated memory (fp16): weights={mem['weights_gb']:.2f}GB, "
          f"gradients={mem['gradients_gb']:.2f}GB, optimizer={mem['optimizer_gb']:.2f}GB, "
          f"total={mem['total_base_gb']:.2f}GB")
    optimal_tokens = chinchilla_optimal_tokens(num_params)
    print(f"Chinchilla optimal training tokens: {optimal_tokens:,}")
    print("NOTE: Training a 40B-class model requires multi-node GPU clusters.")
    print("      This code is structurally ready but realistically infeasible on a single machine.")

    model = LLM(config).to(device)
    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}")

    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    dataset = TextDataset(config["train_file"], tokenizer, block_size=config.get("max_position_embeddings", 2048))
    dataloader = DataLoader(dataset, batch_size=config.get("batch_size", 1), shuffle=True,
                            num_workers=0, pin_memory=(device == "cuda"), collate_fn=lambda b: collate_fn(b, pad_token_id))

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.get("lr", 3e-4), betas=(0.9, 0.95), weight_decay=0.1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=len(dataloader) * config.get("epochs", 1))
    scaler = GradScaler(enabled=(device == "cuda") and config.get("mixed_precision", True))

    accumulation_steps = config.get("gradient_accumulation_steps", 1)
    checkpoint_dir = config.get("checkpoint_dir", "checkpoints")
    checkpoint_interval = config.get("checkpoint_interval", 1000)

    model.train()
    global_step = 0
    for epoch in range(config.get("epochs", 1)):
        total_loss = 0.0
        for i, batch in enumerate(dataloader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            with autocast(enabled=(device == "cuda") and config.get("mixed_precision", True)):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=config.get("gradient_checkpointing", False))
                loss = outputs["loss"] / accumulation_steps
            scaler.scale(loss).backward()
            if (i + 1) % accumulation_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()
                global_step += 1
                if global_step % checkpoint_interval == 0:
                    save_checkpoint(model, optimizer, scheduler, global_step, checkpoint_dir)
            total_loss += loss.item() * accumulation_steps
            if i % 100 == 0:
                print(f"Step {i}, Loss: {loss.item() * accumulation_steps:.4f}")
        print(f"Epoch {epoch + 1}, Loss: {total_loss / len(dataloader):.4f}")

    save_path = config.get("output_dir", "model_40b.pt")
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")


if __name__ == "__main__":
    pretrain()
