import argparse
import hashlib
import json
import logging
import math
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from models.llm.utils.helpers import load_config, save_config, get_device, set_cpu_threads
from models.llm.model.model import LLM
from models.llm.tokenizer.train_tokenizer import load_tokenizer, create_dummy_tokenizer, TextDataset, collate_fn

logger = logging.getLogger(__name__)


class TrialLogger:
    """Append-only JSONL experiment tracker for hyperparameter search."""

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_suffix(".lock")

    def log(self, record: Dict[str, Any]) -> None:
        record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        record.setdefault("trial_id", self._next_id())
        line = json.dumps(record, default=str)
        tmp_path = self.path.with_suffix(".tmp")
        try:
            with open(tmp_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            tmp_path.replace(self.path)
        except OSError:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _next_id(self) -> str:
        if not self.path.exists():
            return "0"
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return str(sum(1 for _ in f))
        except OSError:
            return "0"

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        records: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records


class SearchSpace:
    """Default search space specification and random sampler."""

    @staticmethod
    def default() -> Dict[str, Tuple[str, Any, Any]]:
        return {
            "lr": ("loguniform", 1e-5, 1e-3),
            "warmup_ratio": ("uniform", 0.0, 0.1),
            "batch_size": ("categorical", [1, 2, 4, 8]),
            "max_position_embeddings": ("categorical", [256, 512, 1024, 2048]),
            "gradient_clip_norm": ("categorical", [0.5, 1.0, 5.0]),
            "optimizer": ("categorical", ["adamw", "adam"]),
            "weight_decay": ("loguniform", 1e-5, 0.1),
            "dropout": ("uniform", 0.0, 0.2),
            "initialization": ("categorical", ["normal", "xavier"]),
            "lr_scheduler": ("categorical", ["cosine", "linear", "constant"]),
        }

    @staticmethod
    def sample(search_space: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
        sampled: Dict[str, Any] = {}
        for name, spec in search_space.items():
            kind = spec[0]
            if kind == "loguniform":
                low, high = math.log10(spec[1]), math.log10(spec[2])
                sampled[name] = float(10 ** rng.uniform(low, high))
            elif kind == "uniform":
                sampled[name] = float(rng.uniform(spec[1], spec[2]))
            elif kind == "categorical":
                sampled[name] = rng.choice(spec[1])
            elif kind == "int_uniform":
                sampled[name] = int(rng.randint(spec[1], spec[2]))
            else:
                raise ValueError(f"Unknown search space kind: {kind!r} for {name}")
        return sampled


def _build_optimizer(name: str, params, lr: float, weight_decay: float) -> torch.optim.Optimizer:
    name = name.lower()
    if name == "adamw":
        return torch.optim.AdamW(params, lr=lr, betas=(0.9, 0.95), weight_decay=weight_decay)
    if name == "adam":
        return torch.optim.Adam(params, lr=lr, betas=(0.9, 0.95), weight_decay=weight_decay)
    raise ValueError(f"Unsupported optimizer: {name}")


def _build_scheduler(
    name: str, optimizer: torch.optim.Optimizer, total_steps: int
) -> torch.optim.lr_scheduler.LRScheduler:
    name = name.lower()
    total_steps = max(total_steps, 1)
    if name == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)
    if name == "linear":
        return torch.optim.lr_scheduler.LinearLR(optimizer, start_factor=1.0, end_factor=0.0, total_iters=total_steps)
    if name == "constant":
        return torch.optim.lr_scheduler.ConstantLR(optimizer, factor=1.0)
    raise ValueError(f"Unsupported scheduler: {name}")


def _apply_initialization(model: nn.Module, method: str) -> None:
    method = method.lower()
    if method == "normal":
        for module in model.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif _RMSNorm is not None and isinstance(module, _RMSNorm):
                nn.init.ones_(module.weight)
    elif method == "xavier":
        for module in model.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.xavier_uniform_(module.weight)
    else:
        raise ValueError(f"Unsupported initialization: {method}")


try:
    from models.llm.model.transformer import RMSNorm as _RMSNorm
except Exception:
    _RMSNorm = None


def _ensure_synthetic_data(path: str, min_chars: int = 50000) -> None:
    """Create synthetic training data if it doesn't exist."""
    path_obj = Path(path)
    if path_obj.exists() and path_obj.stat().st_size >= min_chars:
        return
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    sentences = [
        "The transformer architecture relies on self-attention mechanisms for sequence modeling.",
        "Gradient descent optimizes neural network weights by minimizing loss functions.",
        "Dropout regularization prevents overfitting by randomly zeroing activations during training.",
        "Learning rate schedules adjust optimization step sizes to improve convergence.",
        "Batch normalization stabilizes activation distributions across training iterations.",
        "Weight decay penalizes large parameter values to improve generalization.",
        "Adam optimizer adapts learning rates for individual parameters using moving averages.",
        "Cosine annealing gradually reduces learning rates following a cosine curve.",
        "Mixed precision training reduces memory consumption by using lower precision dtypes.",
        "Gradient clipping prevents exploding gradients by norm scaling.",
        "Warmup steps stabilize early training by gradually increasing learning rates.",
        "Embedding layers map discrete tokens to continuous vector representations.",
        "Position encodings add sequence order information to token embeddings.",
        "Layer normalization accelerates convergence by normalizing hidden activations.",
        "Cross-entropy loss measures classification error between predictions and targets.",
        "Softmax activation converts raw logits into probability distributions.",
        "Residual connections ease gradient flow in deep networks by skipping layers.",
        "Multi-head attention learns diverse relational representations across positions.",
        "Feed-forward networks transform hidden states with non-linear expansions.",
        "Checkpointing saves intermediate model states for resumption and evaluation.",
        "Perplexity measures model uncertainty on held-out validation data.",
        "Tokens per second measures training throughput on available hardware.",
        "Backpropagation efficiently computes gradients through the computation graph.",
        "AdamW decouples weight decay from gradient updates for better regularization.",
        "Data loaders batch and shuffle training examples for stochastic optimization.",
        "Vocabulary size determines the number of unique tokens in the tokenizer.",
        "Hidden size controls the dimensionality of internal model representations.",
        "Attention heads partition the hidden dimension for parallel computation.",
        "Feed-forward size scales the intermediate expansion between attention layers.",
        "Sequence length determines the maximum context window the model can process.",
        "Gradient accumulation simulates larger batches when memory is limited.",
        "Mixed precision uses float16 or bfloat16 to speed up training on GPUs.",
        "Validation loss indicates how well the model generalizes to unseen data.",
        "Training loss reflects the model's current error on the training dataset.",
        "Epochs count complete passes over the entire training corpus.",
        "Random seeds ensure reproducible experiments across runs and machines.",
        "Model checkpoints allow resuming training from interrupted states.",
        "Learning rate warmup prevents early instability during optimizer initialization.",
        "Dropout probability controls the fraction of activations randomly masked.",
        "Weight initialization affects optimization dynamics and final model quality.",
    ]
    text = "\n".join(sentences * 2000)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _run_trial(
    config: Dict[str, Any],
    max_steps: int = 50,
    device: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Execute a single training trial and return metrics."""
    if device is None:
        device = get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    torch.manual_seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    train_file = config.get("train_file", "data/train.txt")
    block_size = int(config.get("max_position_embeddings", 1024))
    if not os.path.exists(train_file):
        _ensure_synthetic_data(train_file, min_chars=block_size * 200)

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        create_dummy_tokenizer(
            save_dir=os.path.dirname(tokenizer_path) or ".",
            vocab_size=int(config.get("vocab_size", 1000)),
        )
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    dataset = TextDataset(train_file, tokenizer, block_size=block_size)
    n = len(dataset)
    if n < 2:
        raise ValueError(f"Dataset too small for search: {n} samples at {train_file}")

    g = torch.Generator().manual_seed(seed)
    indices = torch.randperm(n, generator=g).tolist()
    split = max(int(n * 0.9), 1)
    train_dataset = Subset(dataset, indices[:split])
    val_dataset = Subset(dataset, indices[split:])
    if len(val_dataset) < 1:
        val_dataset = Subset(dataset, indices[:max(1, split // 2)])

    batch_size = int(config.get("batch_size", 2))
    accumulation_steps = int(config.get("gradient_accumulation_steps", 1))
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=(device == "cuda"),
        collate_fn=lambda b: collate_fn(b, pad_token_id),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=max(1, batch_size // 2),
        shuffle=False,
        num_workers=0,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
        drop_last=False,
    )

    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    init_method = config.get("initialization", "normal")
    _apply_initialization(model, init_method)

    lr = float(config.get("lr", 3e-4))
    weight_decay = float(config.get("weight_decay", 0.1))
    optimizer = _build_optimizer(config.get("optimizer", "adamw"), model.parameters(), lr, weight_decay)

    total_steps = max(len(train_loader) * int(config.get("epochs", 1)), 1)
    scheduler = _build_scheduler(config.get("lr_scheduler", "cosine"), optimizer, total_steps)

    grad_clip = float(config.get("gradient_clip_norm", 1.0))
    warmup_steps = int(config.get("warmup_steps", 0))
    if warmup_steps == 0 and "warmup_ratio" in config:
        warmup_steps = max(int(total_steps * float(config["warmup_ratio"])), 0)

    use_amp = device == "cuda" and config.get("mixed_precision", "none") != "none"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    model.train()
    global_step = 0
    train_loss_sum = 0.0
    train_tokens = 0
    nan_encountered = False
    intermediate_losses: List[float] = []

    max_steps = min(max_steps, total_steps) if total_steps > 0 else max_steps
    if max_steps <= 0:
        max_steps = 1

    epochs = int(config.get("epochs", 1))
    for _ in range(epochs):
        for i, batch in enumerate(train_loader):
            if global_step >= max_steps:
                break
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)

            with torch.cuda.amp.autocast(enabled=use_amp):
                outputs = model(input_ids, labels=labels, use_gradient_checkpointing=bool(config.get("gradient_checkpointing", False)))
                loss = outputs["loss"] / accumulation_steps

            if torch.isnan(loss) or torch.isinf(loss):
                nan_encountered = True
                break

            scaler.scale(loss).backward()

            if (i + 1) % accumulation_steps == 0:
                scaler.unscale_(optimizer)
                try:
                    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip).item()
                except RuntimeError as exc:
                    msg = str(exc).lower()
                    if "nan" in msg or "inf" in msg:
                        nan_encountered = True
                        break
                    raise
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                scheduler.step()
                global_step += 1

                if warmup_steps > 0 and global_step <= warmup_steps:
                    factor = global_step / warmup_steps
                    for group in optimizer.param_groups:
                        group["lr"] = lr * factor

            train_loss_sum += loss.item() * labels.numel()
            train_tokens += labels.numel()

            if global_step > 0 and global_step % max(1, max_steps // 4) == 0:
                intermediate_losses.append(float(loss.item()))

    if nan_encountered or train_tokens == 0:
        return {
            "val_loss": float("inf"),
            "val_ppl": float("inf"),
            "train_loss": float("inf"),
            "global_step": global_step,
            "intermediate_losses": intermediate_losses,
            "nan_encountered": True,
        }

    model.eval()
    val_loss_sum = 0.0
    val_tokens = 0
    correct = 0
    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            labels = batch["labels"].to(device, non_blocking=True)
            outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
            loss = outputs["loss"].item()
            logits = outputs["logits"]
            val_loss_sum += loss * labels.numel()
            val_tokens += labels.numel()
            preds = logits.argmax(dim=-1)
            mask = labels != -100
            correct += (preds[mask] == labels[mask]).sum().item()
    model.train()

    val_loss = val_loss_sum / max(val_tokens, 1)
    train_loss = train_loss_sum / max(train_tokens, 1)
    try:
        val_ppl = math.exp(min(val_loss, 80))
    except OverflowError:
        val_ppl = float("inf")

    return {
        "val_loss": val_loss,
        "val_ppl": val_ppl,
        "train_loss": train_loss,
        "global_step": global_step,
        "intermediate_losses": intermediate_losses,
        "nan_encountered": False,
    }


class HyperparameterSearch:
    """Optuna-backed (with random-search fallback) hyperparameter search for LLM training."""

    def __init__(
        self,
        base_config_path: Union[str, Path],
        search_space: Optional[Dict[str, Any]] = None,
        n_trials: int = 20,
        output_dir: Union[str, Path] = "hyperparameter_search",
        study_name: str = "llm_search",
        direction: str = "minimize",
        seed: int = 42,
        max_trial_steps: int = 50,
    ) -> None:
        self.base_config_path = Path(base_config_path)
        self.search_space = search_space or SearchSpace.default()
        self.n_trials = int(n_trials)
        self.output_dir = Path(output_dir)
        self.study_name = study_name
        self.direction = direction
        self.seed = int(seed)
        self.max_trial_steps = int(max_trial_steps)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / f"{study_name}.jsonl"
        self.report_path = self.output_dir / f"{study_name}_report.md"
        self.best_config_path = self.output_dir / f"{study_name}_best_config.yaml"

        self.logger = TrialLogger(self.log_path)
        self.rng = random.Random(self.seed)
        self.best_value = float("inf") if direction == "minimize" else float("-inf")
        self.best_config: Optional[Dict[str, Any]] = None
        self.trials: List[Dict[str, Any]] = []

    def _get_base_config(self) -> Dict[str, Any]:
        if not self.base_config_path.exists():
            raise FileNotFoundError(f"Base config not found: {self.base_config_path}")
        return load_config(str(self.base_config_path))

    def _merge_params(self, base: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        config = dict(base)
        for key, value in params.items():
            if key == "max_position_embeddings":
                config["max_position_embeddings"] = int(value)
            elif key == "batch_size":
                config["batch_size"] = int(value)
            elif key == "gradient_clip_norm":
                config["gradient_clip_norm"] = float(value)
            elif key == "warmup_ratio":
                config.pop("warmup_steps", None)
                config["warmup_ratio"] = float(value)
            else:
                config[key] = value
        config.setdefault("epochs", 1)
        config.setdefault("gradient_accumulation_steps", 1)
        config.setdefault("gradient_checkpointing", False)
        config.setdefault("mixed_precision", "none")
        config.setdefault("vocab_size", config.get("vocab_size", 1000))
        config.setdefault("hidden_size", config.get("hidden_size", 256))
        config.setdefault("num_hidden_layers", config.get("num_hidden_layers", 4))
        config.setdefault("num_attention_heads", config.get("num_attention_heads", 4))
        config.setdefault("intermediate_size", config.get("intermediate_size", 1024))
        config.setdefault("layer_norm_epsilon", config.get("layer_norm_epsilon", 1e-5))
        config.setdefault("dropout", config.get("dropout", 0.0))
        config.setdefault("output_dir", str(self.output_dir / "models" / "trial_models"))
        return config

    def _run_and_log(self, params: Dict[str, Any], trial_id: int) -> Dict[str, Any]:
        base_config = self._get_base_config()
        trial_config = self._merge_params(base_config, params)

        trial_dir = self.output_dir / f"trial_{trial_id:04d}"
        trial_dir.mkdir(parents=True, exist_ok=True)
        trial_config["output_dir"] = str(trial_dir / "model.pt")
        trial_config["checkpoint_dir"] = str(trial_dir / "checkpoints")
        trial_config["log_dir"] = str(trial_dir / "logs")

        start = time.time()
        try:
            metrics = _run_trial(trial_config, max_steps=self.max_trial_steps, seed=self.seed + trial_id)
        except Exception as exc:
            logger.exception("Trial %d failed", trial_id)
            metrics = {
                "val_loss": float("inf"),
                "val_ppl": float("inf"),
                "train_loss": float("inf"),
                "error": str(exc),
            }

        elapsed = time.time() - start
        score = metrics.get("val_loss", float("inf"))
        status = "pruned" if metrics.get("pruned") else ("failed" if metrics.get("error") else "completed")

        record = {
            "trial_id": trial_id,
            "params": params,
            "metrics": metrics,
            "score": score,
            "elapsed_seconds": round(elapsed, 3),
            "status": status,
        }
        self.logger.log(record)
        self.trials.append(record)

        is_better = (score < self.best_value) if self.direction == "minimize" else (score > self.best_value)
        if is_better and not math.isinf(score):
            self.best_value = score
            self.best_config = trial_config
            save_config(trial_config, str(self.best_config_path))
            logger.info("New best trial %d: score=%.6f", trial_id, score)

        return record

    def run_random(self) -> Dict[str, Any]:
        logger.info("Running random search: %d trials", self.n_trials)
        for trial_id in range(self.n_trials):
            params = SearchSpace.sample(self.search_space, self.rng)
            record = self._run_and_log(params, trial_id)
            logger.info(
                "Random trial %d/%d: score=%.6f status=%s",
                trial_id + 1,
                self.n_trials,
                record["score"],
                record.get("status", "unknown"),
            )
        return self._build_result()

    def run_optuna(self) -> Dict[str, Any]:
        try:
            import optuna
            from optuna.pruners import MedianPruner
            from optuna.samplers import TPESampler
        except ImportError as exc:
            raise ImportError(
                "Optuna is not installed. Install it with `pip install optuna` or use --search-type random."
            ) from exc

        def objective(trial: "optuna.Trial") -> float:  # type: ignore[name-defined]
            params: Dict[str, Any] = {}
            for name, spec in self.search_space.items():
                kind = spec[0]
                if kind == "loguniform":
                    params[name] = trial.suggest_float(name, spec[1], spec[2], log=True)
                elif kind == "uniform":
                    params[name] = trial.suggest_float(name, spec[1], spec[2])
                elif kind == "categorical":
                    params[name] = trial.suggest_categorical(name, spec[1])
                elif kind == "int_uniform":
                    params[name] = trial.suggest_int(name, spec[1], spec[2])
                else:
                    raise ValueError(f"Unknown search space kind: {kind!r} for {name}")

            trial_id = trial.number
            base_config = self._get_base_config()
            trial_config = self._merge_params(base_config, params)

            trial_dir = self.output_dir / f"trial_{trial_id:04d}"
            trial_dir.mkdir(parents=True, exist_ok=True)
            trial_config["output_dir"] = str(trial_dir / "model.pt")
            trial_config["checkpoint_dir"] = str(trial_dir / "checkpoints")
            trial_config["log_dir"] = str(trial_dir / "logs")

            start = time.time()
            try:
                metrics = _run_trial(trial_config, max_steps=self.max_trial_steps, seed=self.seed + trial_id)
            except Exception as exc:
                logger.exception("Optuna trial %d failed", trial_id)
                raise optuna.TrialPruned(f"Trial failed: {exc}") from exc

            elapsed = time.time() - start
            score = float(metrics.get("val_loss", float("inf")))

            intermediate_losses = metrics.get("intermediate_losses", [])
            for step_idx, loss_val in enumerate(intermediate_losses):
                trial.report(float(loss_val), step=step_idx)
                if trial.should_prune():
                    metrics["pruned"] = True
                    raise optuna.TrialPruned()

            record = {
                "trial_id": trial_id,
                "params": params,
                "metrics": metrics,
                "score": score,
                "elapsed_seconds": round(elapsed, 3),
                "status": "pruned" if metrics.get("pruned") else "completed",
            }
            self.logger.log(record)
            self.trials.append(record)

            if score < self.best_value:
                self.best_value = score
                self.best_config = trial_config
                save_config(trial_config, str(self.best_config_path))

            return score

        pruner = MedianPruner(n_startup_trials=min(5, self.n_trials // 2), n_warmup_steps=2, interval_steps=1)
        sampler = TPESampler(seed=self.seed)
        study = optuna.create_study(
            direction=self.direction,
            study_name=self.study_name,
            storage=f"sqlite:///{self.output_dir / f'{self.study_name}.db'}",
            pruner=pruner,
            sampler=sampler,
            load_if_exists=False,
        )
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        if study.best_trial and self.best_config is None:
            self.best_config = self._merge_params(self._get_base_config(), study.best_trial.params)
            save_config(self.best_config, str(self.best_config_path))
        if study.best_trial is not None:
            self.best_value = study.best_trial.value

        return self._build_result()

    def _build_result(self) -> Dict[str, Any]:
        if self.best_config is None:
            self.best_config = self._get_base_config()
        return {
            "best_config": self.best_config,
            "best_value": self.best_value,
            "trials": self.trials,
            "log_path": str(self.log_path),
            "best_config_path": str(self.best_config_path),
            "report_path": str(self.report_path),
        }

    def run(self, search_type: str = "auto") -> Dict[str, Any]:
        if search_type == "random":
            return self.run_random()
        if search_type == "optuna":
            return self.run_optuna()
        try:
            return self.run_optuna()
        except ImportError:
            logger.warning("Optuna not available, falling back to random search")
            return self.run_random()

    def generate_report(self) -> str:
        trials = self.trials
        if not trials:
            return "# Hyperparameter Search Report\n\nNo trials completed.\n"

        lines: List[str] = []
        lines.append("# Hyperparameter Search Report")
        lines.append("")
        lines.append(f"- **Study**: {self.study_name}")
        lines.append(f"- **Direction**: {self.direction}")
        lines.append(f"- **Trials**: {len(trials)}")
        lines.append(f"- **Best Score**: {self.best_value:.6f}")
        lines.append(f"- **Best Config**: `{self.best_config_path}`")
        lines.append(f"- **Log**: `{self.log_path}`")
        lines.append(f"- **Generated**: {datetime.now(timezone.utc).isoformat()}")

        completed = [t for t in trials if t.get("status") == "completed"]
        pruned = [t for t in trials if t.get("status") == "pruned"]
        failed = [t for t in trials if t.get("status") == "failed"]

        lines.append("")
        lines.append("## Summary")
        lines.append(f"- Completed: {len(completed)}")
        lines.append(f"- Pruned: {len(pruned)}")
        lines.append(f"- Failed: {len(failed)}")

        if completed:
            scores = [t["score"] for t in completed if not math.isinf(t["score"])]
            if scores:
                lines.append(f"- Best completed score: {min(scores):.6f}")
                lines.append(f"- Mean completed score: {sum(scores) / len(scores):.6f}")

        lines.append("")
        lines.append("## Top 10 Trials")
        sorted_trials = sorted(trials, key=lambda t: t.get("score", float("inf")))
        for idx, trial in enumerate(sorted_trials[:10], 1):
            lines.append("")
            lines.append(f"### {idx}. Trial {trial['trial_id']} (score={trial['score']:.6f}, status={trial.get('status', 'unknown')})")
            for k, v in trial.get("params", {}).items():
                lines.append(f"- `{k}`: {v}")
            metrics = trial.get("metrics", {})
            val_loss = metrics.get("val_loss")
            train_loss = metrics.get("train_loss")
            lines.append(f"- val_loss: {val_loss:.6f}" if isinstance(val_loss, (int, float)) else "- val_loss: N/A")
            lines.append(f"- train_loss: {train_loss:.6f}" if isinstance(train_loss, (int, float)) else "- train_loss: N/A")
            lines.append(f"- elapsed: {trial.get('elapsed_seconds', 0):.2f}s")

        lines.append("")
        lines.append("## Best Configuration")
        lines.append("")
        if self.best_config:
            for k, v in self.best_config.items():
                lines.append(f"- `{k}`: {v}")

        return "\n".join(lines)
