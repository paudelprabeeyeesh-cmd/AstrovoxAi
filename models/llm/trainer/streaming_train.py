import logging
import os

import torch
import torch.nn as nn
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader
from tqdm import tqdm

from .model.model import LLM
from .tokenizer.train_tokenizer import load_tokenizer
from .utils.helpers import get_device, load_config, set_cpu_threads

logger = logging.getLogger(__name__)


class WeightStreamer:
    def __init__(self, model: nn.Module, device: str = "cpu", offload_dir: str = ".offload"):
        self.model = model
        self.device = device
        self.offload_dir = offload_dir
        self._active = set()
        os.makedirs(offload_dir, exist_ok=True)
        for name, param in model.named_parameters():
            path = os.path.join(offload_dir, name.replace(".", "_") + ".pt")
            if not os.path.exists(path):
                torch.save(param.data.cpu(), path)
            param.data = torch.tensor([], device="meta")
            param.data.share_memory_()
            self._active.add(name)

    def load(self, name: str):
        if name not in self._active:
            return
        path = os.path.join(self.offload_dir, name.replace(".", "_") + ".pt")
        if os.path.exists(path):
            param = dict(self.model.named_parameters())[name]
            param.data = torch.load(path, map_location=self.device, weights_only=True)

    def offload(self, name: str):
        if name not in self._active:
            return
        param = dict(self.model.named_parameters())[name]
        path = os.path.join(self.offload_dir, name.replace(".", "_") + ".pt")
        torch.save(param.data.cpu(), path)
        param.data = torch.tensor([], device="meta")


class StreamingTrainer:
    def __init__(self, config_path: str = "models/llm/configs/config_4b.yaml"):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.device = get_device()
        if self.device == "cpu":
            set_cpu_threads(min(4, os.cpu_count() or 2))
        self.mp = self.config.get("mixed_precision", "none")
        self.dtype = torch.float32
        if self.mp == "bf16" and hasattr(torch, "bfloat16"):
            self.dtype = torch.bfloat16
        elif self.mp == "fp16" and self.device == "cuda":
            self.dtype = torch.float16
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.scaler = None
        self.streamer = None

    def _build_model(self):
        try:
            self.model = LLM(self.config, device=torch.device(self.device), dtype=self.dtype)
        except RuntimeError as exc:
            if "not enough memory" in str(exc):
                logger.warning("CPU memory insufficient; using meta init with streaming")
                self.model = LLM(self.config, device=torch.device("meta"), dtype=self.dtype)
                self.model = self.model.to_empty(device=torch.device(self.device))
                self.model.apply(self.model._init_weights)
                self.streamer = WeightStreamer(self.model, device=self.device)
            else:
                raise

    def _create_optimizer(self):
        name = self.config.get("optimizer", "adamw").lower()
        lr = self.config.get("lr", 3e-4)
        wd = self.config.get("weight_decay", 0.1)
        if name == "adafactor":
            self.optimizer = torch.optim.AdaFactor(self.model.parameters(), lr=lr, weight_decay=wd)
        else:
            self.optimizer = torch.optim.AdamW(
                self.model.parameters(), lr=lr, weight_decay=wd, betas=(0.9, 0.95)
            )
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))

    def _create_scheduler(self, dataloader_len: int):
        name = self.config.get("lr_scheduler", "cosine").lower()
        epochs = self.config.get("epochs", 1)
        warmup = self.config.get("warmup_steps", int(dataloader_len * epochs * 0.01))
        if name == "cosine":
            self.scheduler = torch.optim.lr_scheduler.SequentialLR(
                self.optimizer,
                schedulers=[
                    torch.optim.lr_scheduler.LinearLR(
                        self.optimizer, start_factor=0.1, end_factor=1.0, total_iters=warmup
                    ),
                    torch.optim.lr_scheduler.CosineAnnealingLR(
                        self.optimizer,
                        T_max=dataloader_len * epochs - warmup,
                        eta_min=self.config.get("min_lr", 1e-6),
                    ),
                ],
                milestones=[warmup],
            )
        elif name == "linear":
            self.scheduler = torch.optim.lr_scheduler.LinearLR(
                self.optimizer,
                start_factor=1.0,
                end_factor=0.0,
                total_iters=dataloader_len * epochs,
            )
        else:
            self.scheduler = torch.optim.lr_scheduler.ConstantLR(self.optimizer, factor=1.0)

    def train(self, resume_from: str | None = None):
        self._build_model()
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        train_file = self.config.get("train_file", "data/train.txt")
        train_dataset = StreamingDataset(
            train_file,
            tokenizer,
            block_size=self.config.get("max_position_embeddings", 2048),
            streaming=True,
        )
        val_dataset = StreamingDataset(
            self.config.get("val_file", train_file),
            tokenizer,
            block_size=self.config.get("max_position_embeddings", 2048),
            streaming=True,
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.get("batch_size", 1),
            shuffle=True,
            num_workers=0,
            collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0),
            drop_last=True,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=max(1, self.config.get("batch_size", 1) // 2),
            shuffle=False,
            num_workers=0,
            collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0),
            drop_last=False,
        )
        self._create_optimizer()
        self._create_scheduler(len(train_loader))
        start_epoch = 0
        best_val_loss = float("inf")
        if resume_from and os.path.exists(resume_from):
            start_epoch, best_val_loss = load_checkpoint(
                self.model, self.optimizer, self.scheduler, resume_from, device=self.device
            )
        metrics = {"train_loss": [], "val_loss": [], "val_ppl": [], "val_acc": []}
        accumulation = self.config.get("gradient_accumulation_steps", 1)
        grad_clip = self.config.get("gradient_clip_norm", 1.0)
        for epoch in range(start_epoch, self.config.get("epochs", 1)):
            train_metrics = self._train_epoch(train_loader, accumulation, grad_clip, epoch)
            val_metrics = self._validate(val_loader)
            metrics["train_loss"].append(train_metrics["loss"])
            metrics["val_loss"].append(val_metrics["loss"])
            metrics["val_ppl"].append(val_metrics["perplexity"])
            metrics["val_acc"].append(val_metrics["accuracy"])
            logger.info(
                f"Epoch {epoch+1} | Train loss: {train_metrics['loss']:.4f} | Val loss: {val_metrics['loss']:.4f} | Val ppl: {val_metrics['perplexity']:.2f} | Val acc: {val_metrics['accuracy']:.4f}"
            )
            if val_metrics["loss"] < best_val_loss:
                best_val_loss = val_metrics["loss"]
                save_checkpoint(
                    self.model,
                    self.optimizer,
                    self.scheduler,
                    epoch,
                    best_val_loss,
                    "best.pt",
                    self.config,
                    global_step=epoch,
                )
        output_path = self.config.get("output_dir", "model.pt")
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
        )
        torch.save(self.model.state_dict(), output_path)
        logger.info(f"Model saved to {output_path}")
        return metrics

    def _train_epoch(
        self, dataloader: DataLoader, accumulation_steps: int, grad_clip: float, epoch: int
    ) -> dict[str, float]:
        self.model.train()
        total_loss = 0.0
        tokens = 0
        start = time.time()
        pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}")
        for i, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)
            if self.streamer:
                for name in list(self.streamer._active):
                    self.streamer.load(name)
            if self.mp == "bf16":
                with autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
                    outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=True)
                    loss = outputs["loss"] / accumulation_steps
                loss.backward()
            elif self.mp == "fp16":
                with autocast(device_type="cuda", enabled=True):
                    outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=True)
                    loss = outputs["loss"] / accumulation_steps
                self.scaler.scale(loss).backward()
            else:
                outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=True)
                loss = outputs["loss"] / accumulation_steps
                loss.backward()
            total_loss += loss.item() * accumulation_steps
            tokens += labels.numel()
            if (i + 1) % accumulation_steps == 0:
                if grad_clip > 0:
                    if self.mp == "fp16":
                        self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip)
                if self.mp == "fp16":
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    self.optimizer.step()
                self.optimizer.zero_grad(set_to_none=True)
                if self.scheduler:
                    self.scheduler.step()
                if self.streamer:
                    for name in list(self.streamer._active):
                        self.streamer.offload(name)
                    gc.collect()
            pbar.set_postfix({"loss": f"{total_loss / (i+1):.4f}"})
        elapsed = time.time() - start
        return {
            "loss": total_loss / max(1, len(dataloader)),
            "tokens": tokens,
            "tokens_per_sec": tokens / max(elapsed, 1e-6),
            "time": elapsed,
        }

    @torch.no_grad()
    def _validate(self, dataloader: DataLoader) -> dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        correct = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)
            if self.streamer:
                for name in list(self.streamer._active):
                    self.streamer.load(name)
            if self.mp == "bf16":
                with autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
                    outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
            elif self.mp == "fp16":
                with autocast(device_type="cuda", enabled=True):
                    outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
            else:
                outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
            loss = outputs["loss"].item()
            logits = outputs["logits"]
            total_loss += loss * labels.numel()
            total_tokens += labels.numel()
            preds = logits.argmax(dim=-1)
            mask = labels != -100
            correct += (preds[mask] == labels[mask]).sum().item()
            if self.streamer:
                for name in list(self.streamer._active):
                    self.streamer.offload(name)
                gc.collect()
        avg_loss = total_loss / max(total_tokens, 1)
        accuracy = correct / max(total_tokens, 1)
        perplexity = torch.exp(torch.tensor(avg_loss)).item()
        return {
            "loss": avg_loss,
            "perplexity": perplexity,
            "accuracy": accuracy,
            "tokens": total_tokens,
        }


def main(config_path: str = "models/llm/configs/config_4b.yaml", resume_from: str | None = None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    trainer = StreamingTrainer(config_path)
    return trainer.train(resume_from=resume_from)


if __name__ == "__main__":
    main()
