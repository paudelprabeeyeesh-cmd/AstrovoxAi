from typing import Optional, Dict, Any
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class QATTrainer:
    def __init__(self, model: nn.Module, quantizer, lr: float = 1e-5):
        self.model = model
        self.quantizer = quantizer
        self.lr = lr
        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    def fake_quantize(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                scale = weight.abs().max() / 127.0
                module.weight.data = (weight / scale).round().clamp(-128, 127).to(torch.int8).float() * scale
        return model

    def train_step(self, inputs: torch.Tensor, labels: torch.Tensor) -> float:
        self.optimizer.zero_grad()
        self.fake_quantize(self.model)
        outputs = self.model(inputs)
        loss = nn.functional.cross_entropy(outputs, labels)
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def train_epoch(self, dataloader) -> float:
        total_loss = 0.0
        num_batches = 0
        for batch in dataloader:
            inputs = batch['input_ids'] if isinstance(batch, dict) else batch[0]
            labels = batch['labels'] if isinstance(batch, dict) else batch[1]
            loss = self.train_step(inputs, labels)
            total_loss += loss
            num_batches += 1
        return total_loss / max(1, num_batches)

    def export(self, save_path: str) -> None:
        self.quantizer.quantize(self.model)
        torch.save(self.model.state_dict(), save_path)
        logger.info(f"QAT model exported to {save_path}")
