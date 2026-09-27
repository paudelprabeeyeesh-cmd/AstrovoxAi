import logging
import math

import torch
from torch.utils.data import DataLoader

from ..model.model import LLM

logger = logging.getLogger(__name__)


class Evaluator:
    def __init__(self, model: LLM, tokenizer, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def perplexity(self, dataloader: DataLoader, max_batches: int | None = None) -> float:
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        with torch.no_grad():
            for i, batch in enumerate(dataloader):
                if max_batches is not None and i >= max_batches:
                    break
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)
                outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
                loss = outputs["loss"].item()
                total_loss += loss * labels.numel()
                total_tokens += labels.numel()
        avg_loss = total_loss / max(total_tokens, 1)
        return math.exp(avg_loss) if avg_loss < 100 else float("inf")

    def accuracy(self, dataloader: DataLoader, max_batches: int | None = None) -> float:
        self.model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for i, batch in enumerate(dataloader):
                if max_batches is not None and i >= max_batches:
                    break
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)
                outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
                preds = outputs["logits"].argmax(dim=-1)
                mask = labels != -100
                correct += (preds[mask] == labels[mask]).sum().item()
                total += mask.sum().item()
        return correct / max(total, 1)

    def generation_quality(self, prompts: list[str], max_new_tokens: int = 50) -> dict[str, float]:
        from ..inference.generate import generate

        results = []
        for prompt in prompts:
            text = generate(
                self.model,
                self.tokenizer,
                prompt,
                max_new_tokens=max_new_tokens,
                device=self.device,
            )
            results.append(text)
        return {
            "num_generated": len(results),
            "avg_length": sum(len(r.split()) for r in results) / max(len(results), 1),
        }
