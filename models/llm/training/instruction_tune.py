import os
import json
import random
import logging
from typing import Dict, List, Optional

import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)


class InstructionDataset(Dataset):
    def __init__(self, data_path: str, tokenizer, max_length: int = 2048):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = []
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    self.samples.append(record)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        text = sample.get("text", "")
        encoding = self.tokenizer.encode(text)
        ids = encoding.ids[:self.max_length + 1]
        x = torch.tensor(ids[:-1], dtype=torch.long)
        y = torch.tensor(ids[1:], dtype=torch.long)
        return {"input_ids": x, "labels": y}


class InstructionTuner:
    def __init__(self, model, tokenizer, config: Dict):
        self.model = model
        self.tokenizer = tokenizer
        self.config = config

    def train(self, train_dataset, val_dataset, output_dir: str):
        from ..training.pretrain import train_epoch, validate, save_checkpoint, load_checkpoint, collate_fn
        from torch.utils.data import DataLoader
        train_loader = DataLoader(train_dataset, batch_size=self.config.get("batch_size", 2), shuffle=True, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id=self.tokenizer.token_to_id("<pad>") or 0), drop_last=True)
        val_loader = DataLoader(val_dataset, batch_size=max(1, self.config.get("batch_size", 1)//2), shuffle=False, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id=self.tokenizer.token_to_id("<pad>") or 0), drop_last=False)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.config.get("lr", 3e-4), weight_decay=self.config.get("weight_decay", 0.1))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=len(train_loader) * self.config.get("epochs", 1))
        scaler = torch.cuda.amp.GradScaler(enabled=(self.config.get("mixed_precision") == "fp16"))
        for epoch in range(self.config.get("epochs", 1)):
            train_metrics = train_epoch(self.model, train_loader, optimizer, scheduler, scaler, "cpu", self.config.get("gradient_accumulation_steps", 1), self.config.get("gradient_clip_norm", 1.0), "none", epoch)
            val_metrics = validate(self.model, val_loader, "cpu", max_batches=self.config.get("max_val_batches"), mp="none")
            logger.info(f"Instruct Epoch {epoch+1} | Train loss: {train_metrics['train_loss']:.4f} | Val loss: {val_metrics['loss']:.4f}")
            save_checkpoint(self.model, optimizer, scheduler, epoch, val_metrics["loss"], os.path.join(output_dir, "instruct_best.pt"), self.config, global_step=epoch)
        os.makedirs(output_dir, exist_ok=True)
        torch.save(self.model.state_dict(), os.path.join(output_dir, "instruct_model.pt"))
        logger.info(f"Instruct model saved to {output_dir}")
