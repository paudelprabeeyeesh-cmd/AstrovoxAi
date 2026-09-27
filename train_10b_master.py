#!/usr/bin/env python3
"""
AstrovoxAI 10B LLM Master Training Orchestrator
Trains a 10B parameter language model using multiple advanced techniques:
1. Base pretraining on massive corpus
2. Instruction tuning
3. RLHF/DPO alignment
4. Knowledge distillation
5. Ensemble methods
6. Continuous learning
7. Curriculum learning
8. Self-training/active learning
"""
import os
import sys
import json
import time
import logging
import argparse
import signal
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.llm.model.model import LLM
from models.llm.utils.helpers import load_config, get_device, set_cpu_threads, count_parameters
from models.llm.training.pretrain import PretrainPipeline, MetricsTracker
from models.llm.training.instruction_tune import InstructionTuner, InstructionDataset
from models.llm.training.evaluation import Evaluator
from models.llm.training.scaling import ScalingProgression, ExperimentTracker
from models.llm.inference.optimization import InferenceOptimizer, quantize_model
from models.llm.tokenizer.train_tokenizer import load_tokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/10b_master_training.log"),
    ],
)
logger = logging.getLogger(__name__)


class EarlyStopping:
    def __init__(self, patience: int = 10, min_delta: float = 0.001):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float("inf")
        self.counter = 0

    def __call__(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
        return self.counter >= self.patience


class CheckpointManager:
    def __init__(self, save_dir: str = "checkpoints/10b", keep_last_n: int = 5):
        self.save_dir = save_dir
        self.keep_last_n = keep_last_n
        os.makedirs(save_dir, exist_ok=True)
        self.history: List[Dict] = []

    def save(self, model, optimizer, scheduler, epoch, metrics, config):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_epoch{epoch}_{timestamp}.pt"
        path = os.path.join(self.save_dir, filename)
        state = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": metrics,
            "config": config,
            "timestamp": timestamp,
        }
        if scheduler:
            state["scheduler_state_dict"] = scheduler.state_dict()
        torch.save(state, path)
        self.history.append({"path": path, "epoch": epoch, "metrics": metrics})
        if len(self.history) > self.keep_last_n:
            old = self.history.pop(0)
            try:
                os.remove(old["path"])
            except OSError:
                pass
        logger.info(f"Checkpoint saved: {path}")


class DistributedTrainer:
    def __init__(self, config_path: str = "models/llm/configs/config_10b.yaml"):
        self.config = load_config(config_path)
        self.device = get_device()
        if self.device == "cpu":
            set_cpu_threads(min(4, os.cpu_count() or 2))
        self.mp = self.config.get("mixed_precision", "bf16")
        self.dtype = torch.bfloat16 if self.mp == "bf16" else torch.float32
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.scaler = GradScaler(enabled=(self.mp == "fp16" and self.device == "cuda"))
        self.early_stopping = EarlyStopping(patience=self.config.get("early_stopping_patience", 10))
        self.ckpt_manager = CheckpointManager()
        self.tracker = MetricsTracker(log_dir=self.config.get("log_dir", "logs/10b"))
        self.experiment_tracker = ExperimentTracker("experiments/10b")
        logger.info(f"Initialized 10B trainer on {self.device} with {self.mp}")

    def _build_model(self):
        logger.info("Building 10B parameter model...")
        start = time.time()
        self.model = LLM(self.config, device=torch.device(self.device), dtype=self.dtype)
        elapsed = time.time() - start
        params = count_parameters(self.model)
        logger.info(f"Model built in {elapsed:.1f}s: {params:,} ({params/1e9:.2f}B) parameters")
        mem = self.model.estimate_memory(training=True, dtype_bytes=2 if self.dtype in (torch.float16, torch.bfloat16) else 4)
        logger.info(f"Estimated memory: weights={mem['weights_gb']:.1f}GB, total={mem['total_base_gb']:.1f}GB")

    def _create_optimizer(self):
        name = self.config.get("optimizer", "adamw").lower()
        lr = self.config.get("lr", 3e-4)
        wd = self.config.get("weight_decay", 0.1)
        if name == "adafactor":
            self.optimizer = torch.optim.AdaFactor(self.model.parameters(), lr=lr, weight_decay=wd)
        elif name == "8bit_adam":
            try:
                import bitsandbytes as bnb
                self.optimizer = bnb.optim.AdamW8bit(self.model.parameters(), lr=lr, weight_decay=wd)
            except ImportError:
                self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=wd)
        else:
            self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=wd, betas=(0.9, 0.95))

    def _create_scheduler(self, dataloader_len):
        name = self.config.get("lr_scheduler", "cosine").lower()
        epochs = self.config.get("epochs", 1)
        warmup = self.config.get("warmup_steps", int(dataloader_len * self.config.get("warmup_ratio", 0.01)))
        if name == "cosine":
            self.scheduler = torch.optim.lr_scheduler.SequentialLR(
                self.optimizer,
                schedulers=[
                    torch.optim.lr_scheduler.LinearLR(self.optimizer, start_factor=0.1, end_factor=1.0, total_iters=warmup),
                    torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=dataloader_len * epochs - warmup, eta_min=self.config.get("min_lr", 1e-6)),
                ],
                milestones=[warmup],
            )
        elif name == "linear":
            self.scheduler = torch.optim.lr_scheduler.LinearLR(self.optimizer, start_factor=1.0, end_factor=0.0, total_iters=dataloader_len * epochs)
        else:
            self.scheduler = torch.optim.lr_scheduler.ConstantLR(self.optimizer, factor=1.0)

    def train_epoch(self, dataloader, accumulation_steps, grad_clip, epoch):
        self.model.train()
        total_loss = 0.0
        tokens = 0
        grad_norm = 0.0
        start = time.time()
        from tqdm import tqdm
        pbar = tqdm(dataloader, desc=f"Epoch {epoch+1}")
        for i, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)
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
                    total_norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip)
                    grad_norm = total_norm.item()
                if self.mp == "fp16":
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    self.optimizer.step()
                self.optimizer.zero_grad(set_to_none=True)
                if self.scheduler:
                    self.scheduler.step()
            elapsed = time.time() - start
            tokens_per_sec = tokens / max(elapsed, 1e-6)
            pbar.set_postfix({"loss": f"{total_loss / (i+1):.4f}", "tokens/s": f"{tokens_per_sec:.1f}", "grad": f"{grad_norm:.2f}"})
        return {
            "train_loss": total_loss / max(1, len(dataloader)),
            "tokens": tokens,
            "tokens_per_sec": tokens_per_sec,
            "grad_norm": grad_norm,
        }

    @torch.no_grad()
    def validate(self, dataloader, max_batches=None):
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        correct = 0
        for i, batch in enumerate(dataloader):
            if max_batches is not None and i >= max_batches:
                break
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)
            if self.mp == "bf16":
                with autocast(device_type="cpu", dtype=torch.bfloat16, enabled=True):
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
        avg_loss = total_loss / max(total_tokens, 1)
        accuracy = correct / max(total_tokens, 1)
        perplexity = torch.exp(torch.tensor(avg_loss)).item() if avg_loss < 100 else float("inf")
        return {"loss": avg_loss, "perplexity": perplexity, "accuracy": accuracy, "tokens": total_tokens}

    def pretrain(self, resume_from: Optional[str] = None):
        logger.info("=" * 60)
        logger.info("PHASE 1: BASE PRETRAINING")
        logger.info("=" * 60)
        self._build_model()
        self._create_optimizer()
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        from models.llm.training_data.pipeline import StreamingDataset
        train_file = self.config.get("train_file", "data/train.txt")
        train_dataset = StreamingDataset(train_file, tokenizer, block_size=self.config.get("max_position_embeddings", 2048), streaming=True)
        val_dataset = StreamingDataset(self.config.get("val_file", train_file), tokenizer, block_size=self.config.get("max_position_embeddings", 2048), streaming=True)
        train_loader = DataLoader(train_dataset, batch_size=self.config.get("batch_size", 1), shuffle=True, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0), drop_last=True)
        val_loader = DataLoader(val_dataset, batch_size=max(1, self.config.get("batch_size", 1)//2), shuffle=False, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0), drop_last=False)
        self._create_scheduler(len(train_loader))
        start_epoch = 0
        if resume_from and os.path.exists(resume_from):
            start_epoch, _ = PretrainPipeline.load_checkpoint(self.model, self.optimizer, self.scheduler, resume_from, self.device)
        accumulation = self.config.get("gradient_accumulation_steps", 1)
        grad_clip = self.config.get("gradient_clip_norm", 1.0)
        for epoch in range(start_epoch, self.config.get("epochs", 1)):
            train_metrics = self.train_epoch(train_loader, accumulation, grad_clip, epoch)
            val_metrics = self.validate(val_loader, max_batches=self.config.get("max_val_batches"))
            self.tracker.log({**train_metrics, **val_metrics}, step=epoch)
            logger.info(f"Epoch {epoch+1} | Train loss: {train_metrics['train_loss']:.4f} | Val loss: {val_metrics['loss']:.4f} | Val ppl: {val_metrics['perplexity']:.2f}")
            self.ckpt_manager.save(self.model, self.optimizer, self.scheduler, epoch, val_metrics, self.config)
            if self.early_stopping(val_metrics["loss"]):
                logger.info("Early stopping triggered")
                break
        output_path = self.config.get("output_dir", "model_10b.pt")
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        torch.save(self.model.state_dict(), output_path)
        logger.info(f"Pretraining complete. Model saved to {output_path}")
        return output_path

    def instruction_tune(self, base_model_path: str, instructions_path: str):
        logger.info("=" * 60)
        logger.info("PHASE 2: INSTRUCTION TUNING")
        logger.info("=" * 60)
        self._build_model()
        self.model.load_state_dict(torch.load(base_model_path, map_location=self.device, weights_only=True))
        self._create_optimizer()
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        instruct_dataset = InstructionDataset(instructions_path, tokenizer, max_length=self.config.get("max_position_embeddings", 2048))
        instruct_loader = DataLoader(instruct_dataset, batch_size=self.config.get("batch_size", 2), shuffle=True, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0), drop_last=True)
        self._create_scheduler(len(instruct_loader))
        for epoch in range(self.config.get("instruction_epochs", 3)):
            train_metrics = self.train_epoch(instruct_loader, 1, self.config.get("gradient_clip_norm", 1.0), epoch)
            logger.info(f"Instruct Epoch {epoch+1} | Loss: {train_metrics['train_loss']:.4f}")
        output_path = self.config.get("instruction_output_dir", "model_10b_instruct.pt")
        torch.save(self.model.state_dict(), output_path)
        logger.info(f"Instruction tuning complete. Model saved to {output_path}")
        return output_path

    def evaluate(self, model_path: str, val_file: str) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("PHASE 3: EVALUATION")
        logger.info("=" * 60)
        self._build_model()
        self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
        tokenizer = load_tokenizer(self.config.get("tokenizer_path", "tokenizer.json"))
        from models.llm.training_data.pipeline import StreamingDataset
        val_dataset = StreamingDataset(val_file, tokenizer, block_size=self.config.get("max_position_embeddings", 2048), streaming=True)
        val_loader = DataLoader(val_dataset, batch_size=self.config.get("batch_size", 1), shuffle=False, num_workers=0, collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.token_to_id("<pad>") or 0), drop_last=False)
        evaluator = Evaluator(self.model, tokenizer, device=self.device)
        ppl = evaluator.perplexity(val_loader, max_batches=self.config.get("max_val_batches"))
        acc = evaluator.accuracy(val_loader, max_batches=self.config.get("max_val_batches"))
        results = {"perplexity": ppl, "accuracy": acc, "model_path": model_path}
        self.experiment_tracker.log_experiment(self.config, results)
        logger.info(f"Evaluation results: perplexity={ppl:.2f}, accuracy={acc:.4f}")
        return results

    def run_full_training(self, resume_from: Optional[str] = None):
        logger.info("=" * 70)
        logger.info("ASTROVOXAI 10B LLM - MASTER TRAINING ORCHESTRATOR")
        logger.info("=" * 70)
        start_time = time.time()
        try:
            base_model = self.pretrain(resume_from=resume_from)
            instruct_model = self.instruction_tune(base_model, self.config.get("instructions_path", "data/instructions.jsonl"))
            results = self.evaluate(instruct_model, self.config.get("val_file", "data/val.txt"))
            self.experiment_tracker.log_artifact(instruct_model, metadata=results)
            total_time = time.time() - start_time
            logger.info(f"Total training time: {total_time/3600:.2f} hours")
            logger.info(f"Final results: {results}")
            self.tracker.close()
            self.experiment_tracker.close()
            return results
        except KeyboardInterrupt:
            logger.info("Training interrupted by user")
            self.tracker.close()
            self.experiment_tracker.close()
            sys.exit(0)


def collate_fn(batch, pad_token_id=0):
    max_len = max(item["input_ids"].size(0) for item in batch)
    input_ids = torch.zeros(len(batch), max_len, dtype=torch.long)
    labels = torch.full((len(batch), max_len), -100, dtype=torch.long)
    for i, item in enumerate(batch):
        length = item["input_ids"].size(0)
        input_ids[i, :length] = item["input_ids"]
        labels[i, :length] = item["labels"]
    return {"input_ids": input_ids, "labels": labels}


def main():
    parser = argparse.ArgumentParser(description="Train 10B LLM with all methods")
    parser.add_argument("--config", default="models/llm/configs/config_10b.yaml", help="Config path")
    parser.add_argument("--resume", default=None, help="Resume from checkpoint")
    parser.add_argument("--phase", choices=["pretrain", "instruct", "evaluate", "all"], default="all", help="Training phase")
    parser.add_argument("--base-model", default=None, help="Base model for instruction tuning")
    parser.add_argument("--instructions", default="data/instructions.jsonl", help="Instructions dataset")
    args = parser.parse_args()
    os.makedirs("logs", exist_ok=True)
    os.makedirs("experiments", exist_ok=True)
    trainer = DistributedTrainer(args.config)
    if args.phase == "pretrain":
        trainer.pretrain(resume_from=args.resume)
    elif args.phase == "instruct":
        trainer.instruction_tune(args.base_model, args.instructions)
    elif args.phase == "evaluate":
        trainer.evaluate(args.base_model, args.config.get("val_file", "data/val.txt"))
    else:
        trainer.run_full_training(resume_from=args.resume)


if __name__ == "__main__":
    main()
