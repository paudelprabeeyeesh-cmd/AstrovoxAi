from typing import Dict, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SFTTrainer:
    def __init__(self, model: nn.Module, tokenizer, lr: float = 5e-5, max_length: int = 2048):
        self.model = model
        self.tokenizer = tokenizer
        self.lr = lr
        self.max_length = max_length
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    def prepare_batch(self, prompts: List[str], completions: List[str]) -> Dict[str, torch.Tensor]:
        texts = [p + c for p, c in zip(prompts, completions)]
        encodings = self.tokenizer(texts, padding=True, truncation=True, max_length=self.max_length, return_tensors='pt')
        labels = encodings['input_ids'].clone()
        for i, prompt in enumerate(prompts):
            prompt_len = len(self.tokenizer.encode(prompt, truncation=True, max_length=self.max_length))
            labels[i, :prompt_len] = -100
        encodings['labels'] = labels
        return encodings

    def train_step(self, prompts: List[str], completions: List[str]) -> float:
        batch = self.prepare_batch(prompts, completions)
        self.optimizer.zero_grad()
        outputs = self.model(**batch)
        loss = outputs.loss
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def train_epoch(self, dataloader) -> float:
        total_loss = 0.0
        num_batches = 0
        for batch in dataloader:
            prompts = batch['prompts']
            completions = batch['completions']
            loss = self.train_step(prompts, completions)
            total_loss += loss
            num_batches += 1
        return total_loss / max(1, num_batches)

    def save(self, path: str) -> None:
        torch.save(self.model.state_dict(), path)
        logger.info(f"SFT model saved to {path}")
