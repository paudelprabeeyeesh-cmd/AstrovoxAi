import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from model.model import LLM
from tokenizer.train_tokenizer import TextDataset, collate_fn, load_tokenizer
from utils.helpers import load_config, get_device
from trainer.checkpoint import save_checkpoint, load_checkpoint
from trainer.metrics import compute_perplexity


class InstructionDataset(torch.utils.data.Dataset):
    def __init__(self, file_path, tokenizer, block_size=2048):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.examples = []
        tokens = tokenizer.encode(text)
        for i in range(0, len(tokens) - block_size, block_size):
            self.examples.append(torch.tensor(tokens[i:i + block_size], dtype=torch.long))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        x = self.examples[idx]
        return {"input_ids": x, "labels": x}


def finetune(config_path="configs/config_40b.yaml", instruction_file="data/instructions.jsonl"):
    config = load_config(config_path)
    device = get_device()
    model = LLM(config).to(device)

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    dataset = InstructionDataset(instruction_file, tokenizer, block_size=config.get("max_position_embeddings", 2048))
    dataloader = DataLoader(dataset, batch_size=config.get("batch_size", 1), shuffle=True,
                            num_workers=0, pin_memory=(device == "cuda"), collate_fn=lambda b: collate_fn(b, pad_token_id))

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.get("finetune_lr", 1e-5),
                                   betas=(0.9, 0.95), weight_decay=0.1)
    scaler = GradScaler(enabled=(device == "cuda"))

    accumulation_steps = config.get("gradient_accumulation_steps", 1)
    checkpoint_dir = config.get("checkpoint_dir", "checkpoints")

    model.train()
    for epoch in range(config.get("finetune_epochs", 3)):
        total_loss = 0.0
        for i, batch in enumerate(dataloader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            with autocast(enabled=(device == "cuda")):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
                loss = outputs["loss"] / accumulation_steps
            scaler.scale(loss).backward()
            if (i + 1) % accumulation_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
            total_loss += loss.item() * accumulation_steps
        ppl = compute_perplexity(model, dataloader, device)
        print(f"Epoch {epoch + 1}, Loss: {total_loss / len(dataloader):.4f}, Perplexity: {ppl:.2f}")
        save_checkpoint(model, optimizer, None, epoch + 1, checkpoint_dir, prefix="finetune")


if __name__ == "__main__":
    finetune()
