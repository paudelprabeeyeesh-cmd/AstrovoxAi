import gc
import logging
import os

import torch
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader
from tqdm import tqdm

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import get_device, load_config, set_cpu_threads

logger = logging.getLogger(__name__)


class AdaFactor(torch.optim.Optimizer):
    def __init__(
        self,
        params,
        lr=1e-3,
        beta1=0.0,
        beta2=0.999,
        eps1=1e-30,
        eps2=1e-3,
        clip_threshold=1.0,
        weight_decay=0.0,
        scale_parameter=True,
    ):
        defaults = {
            "lr": lr,
            "beta1": beta1,
            "beta2": beta2,
            "eps1": eps1,
            "eps2": eps2,
            "clip_threshold": clip_threshold,
            "weight_decay": weight_decay,
            "scale_parameter": scale_parameter,
        }
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                grad = p.grad
                state = self.state[p]

                if len(state) == 0:
                    state["step"] = 0
                    state["exp_avg_sq_row"] = None
                    state["exp_avg_sq_col"] = None
                    if group["beta1"] > 0:
                        state["exp_avg"] = torch.zeros_like(p.data)

                state["step"] += 1
                beta1 = group["beta1"]
                beta2 = group["beta2"]
                eps1 = group["eps1"]
                eps2 = group["eps2"]
                clip_threshold = group["clip_threshold"]
                weight_decay = group["weight_decay"]
                scale_parameter = group.get("scale_parameter", True)

                if weight_decay > 0:
                    p.data.mul_(1 - group["lr"] * weight_decay)

                if len(grad.shape) >= 2:
                    grad_sq = grad * grad
                    if state["exp_avg_sq_row"] is None:
                        state["exp_avg_sq_row"] = torch.ones(grad.shape[:-1], device=grad.device)
                        state["exp_avg_sq_col"] = torch.ones(
                            grad.shape[:-2] + grad.shape[-1:], device=grad.device
                        )

                    state["exp_avg_sq_row"] = beta2 * state["exp_avg_sq_row"] + (
                        1 - beta2
                    ) * grad_sq.mean(dim=-1)
                    state["exp_avg_sq_col"] = beta2 * state["exp_avg_sq_col"] + (
                        1 - beta2
                    ) * grad_sq.mean(dim=-2)

                    r = state["exp_avg_sq_row"] / (1 - beta2 ** state["step"])
                    c = state["exp_avg_sq_col"] / (1 - beta2 ** state["step"])

                    u = grad / (torch.sqrt(r.unsqueeze(-1) * c.unsqueeze(-2)) + eps1)
                else:
                    grad_sq = grad * grad
                    if "exp_avg_sq" not in state:
                        state["exp_avg_sq"] = torch.ones_like(grad)
                    state["exp_avg_sq"] = beta2 * state["exp_avg_sq"] + (1 - beta2) * grad_sq
                    u = grad / (
                        torch.sqrt(state["exp_avg_sq"] / (1 - beta2 ** state["step"])) + eps1
                    )

                if clip_threshold > 0:
                    u_norm = u.norm()
                    if u_norm > clip_threshold:
                        u = u * clip_threshold / u_norm

                if beta1 > 0:
                    if "exp_avg" not in state:
                        state["exp_avg"] = torch.zeros_like(p.data)
                    state["exp_avg"] = beta1 * state["exp_avg"] + (1 - beta1) * u
                    u = state["exp_avg"]

                if scale_parameter:
                    param_rms = p.norm()
                    lr = group["lr"] * max(eps2, param_rms)
                else:
                    lr = group["lr"]

                p.data.add_(u, alpha=-lr)

        return loss


class MetaLLM(LLM):
    def __init__(
        self,
        config: dict,
        device: torch.device = None,
        dtype: torch.dtype = None,
        cache_dir: str = ".weight_cache",
    ):
        self._cache_dir = cache_dir
        self._loaded = set()
        os.makedirs(cache_dir, exist_ok=True)
        super().__init__(config, device=torch.device("meta"), dtype=dtype)
        self._device = device or torch.device("cpu")
        self._dtype = dtype or torch.float32
        self._cache_weights()

    def _param_name(self, name: str) -> str:
        return os.path.join(self._cache_dir, name.replace(".", "_") + ".pt")

    def _cache_weights(self):
        for name, param in self.named_parameters():
            path = self._param_name(name)
            if not os.path.exists(path):
                torch.save(torch.zeros_like(param.data, device="cpu"), path)
            param.data = torch.tensor([], device="meta")

    def _load_weights(self, names: list[str]):
        for name in names:
            if name in self._loaded:
                continue
            param = dict(self.named_parameters())[name]
            path = self._param_name(name)
            if os.path.exists(path):
                param.data = torch.load(path, map_location="cpu", weights_only=True)
                self._loaded.add(name)

    def _offload_weights(self, names: list[str]):
        for name in names:
            if name not in self._loaded:
                continue
            param = dict(self.named_parameters())[name]
            path = self._param_name(name)
            torch.save(param.data.cpu(), path)
            param.data = torch.tensor([], device="meta")
            self._loaded.discard(name)
        gc.collect()

    def forward(
        self,
        input_ids: torch.Tensor,
        labels=None,
        attention_mask=None,
        use_gradient_checkpointing=False,
    ):
        names = [n for n, _ in self.named_parameters()]
        self._load_weights(names)
        try:
            return super().forward(
                input_ids,
                labels=labels,
                attention_mask=attention_mask,
                use_gradient_checkpointing=use_gradient_checkpointing,
            )
        finally:
            if not self.training:
                self._offload_weights(names)


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

    def _build_model(self):
        try:
            self.model = MetaLLM(self.config, device=torch.device(self.device), dtype=self.dtype)
            logger.info("Meta model built and cached")
        except RuntimeError as exc:
            if "not enough memory" in str(exc):
                logger.warning("Reducing model size for CPU")
                cfg = dict(self.config)
                cfg["hidden_size"] = min(cfg.get("hidden_size", 2880), 2560)
                cfg["num_hidden_layers"] = min(cfg.get("num_hidden_layers", 32), 24)
                cfg["intermediate_size"] = min(cfg.get("intermediate_size", 9216), 8192)
                self.config = cfg
                self.model = MetaLLM(
                    self.config, device=torch.device(self.device), dtype=self.dtype
                )
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

    def _train_epoch(self, dataloader, accumulation_steps, grad_clip, epoch):
        self.model.train()
        total_loss = 0.0
        tokens = 0
        start = time.time()
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
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip)
                if self.mp == "fp16":
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    self.optimizer.step()
                self.optimizer.zero_grad(set_to_none=True)
                if self.scheduler:
                    self.scheduler.step()
            pbar.set_postfix({"loss": f"{total_loss / (i+1):.4f}"})
        elapsed = time.time() - start
        return {
            "loss": total_loss / max(1, len(dataloader)),
            "tokens": tokens,
            "tokens_per_sec": tokens / max(elapsed, 1e-6),
            "time": elapsed,
        }

    @torch.no_grad()
    def _validate(self, dataloader):
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        correct = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)
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
        avg_loss = total_loss / max(total_tokens, 1)
        accuracy = correct / max(total_tokens, 1)
        perplexity = torch.exp(torch.tensor(avg_loss)).item()
        return {
            "loss": avg_loss,
            "perplexity": perplexity,
            "accuracy": accuracy,
            "tokens": total_tokens,
        }


def train(config_path="models/llm/configs/config_4b.yaml", resume_from=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    trainer = StreamingTrainer(config_path)
    return trainer.train(resume_from=resume_from)


def pretrain(config_path="models/llm/configs/config_4b.yaml", resume_from=None):
    return train(config_path=config_path, resume_from=resume_from)
