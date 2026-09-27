import contextlib
import logging
import math
import os
import sys

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.cuda.amp import GradScaler, autocast
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
from tqdm import tqdm

from ..model.model import LLM
from ..tokenizer.train_tokenizer import load_tokenizer
from ..utils.helpers import count_parameters, get_device, load_config, set_cpu_threads
from .checkpoint import (
    load_checkpoint,
    remove_old_checkpoints,
    save_checkpoint,
)
from .metrics import MetricsLogger, TrainingMetrics, evaluate_metrics
from .pretrain import AdaFactor

logger = logging.getLogger(__name__)


class LoRALinear(nn.Module):
    def __init__(
        self, linear: nn.Linear, r: int = 8, lora_alpha: float = 16, lora_dropout: float = 0.0
    ):
        super().__init__()
        self.linear = linear
        self.r = r
        self.lora_alpha = lora_alpha
        self.lora_dropout = nn.Dropout(p=lora_dropout) if lora_dropout > 0 else nn.Identity()

        self.linear.weight.requires_grad = False
        if self.linear.bias is not None:
            self.linear.bias.requires_grad = False

        self.lora_A = nn.Parameter(torch.zeros(r, linear.in_features))
        self.lora_B = nn.Parameter(torch.zeros(linear.out_features, r))

        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)

        self.scaling = lora_alpha / r

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        result = self.linear(x)
        if self.r > 0:
            lora = self.lora_dropout(x) @ self.lora_A.T @ self.lora_B.T
            result = result + lora * self.scaling
        return result

    def merge(self):
        if self.r > 0:
            delta = (self.lora_B @ self.lora_A) * self.scaling
            self.linear.weight.data += delta
            self.lora_A = None
            self.lora_B = None


class QLoRALinear(nn.Module):
    def __init__(
        self,
        linear: nn.Linear,
        r: int = 8,
        lora_alpha: float = 16,
        lora_dropout: float = 0.0,
        bits: int = 4,
    ):
        super().__init__()
        self.r = r
        self.lora_alpha = lora_alpha
        self.lora_dropout = nn.Dropout(p=lora_dropout) if lora_dropout > 0 else nn.Identity()
        self.scaling = lora_alpha / r

        try:
            import bitsandbytes as bnb

            self.linear = bnb.nn.Linear4bit(
                linear.in_features,
                linear.out_features,
                bias=linear.bias is not None,
                quant_type="nf4",
            )
            self.linear.weight = linear.weight
            if linear.bias is not None:
                self.linear.bias = linear.bias
            self._qlora = True
        except ImportError:
            self.linear = linear.to(dtype=torch.float16)
            self.linear.weight.requires_grad = False
            if self.linear.bias is not None:
                self.linear.bias.requires_grad = False
            self._qlora = False

        self.lora_A = nn.Parameter(torch.zeros(r, linear.in_features))
        self.lora_B = nn.Parameter(torch.zeros(linear.out_features, r))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base_dtype = self.linear.weight.dtype if hasattr(self.linear, "weight") else x.dtype
        result = self.linear(x.to(base_dtype) if hasattr(self.linear, "weight") else x)
        if self.r > 0:
            lora = self.lora_dropout(x.float()) @ self.lora_A.T @ self.lora_B.T
            result = result + lora * self.scaling
        return result.to(x.dtype)

    def merge(self):
        if self.r > 0:
            delta = (self.lora_B @ self.lora_A) * self.scaling
            if hasattr(self.linear, "weight") and self.linear.weight is not None:
                self.linear.weight.data += delta.to(self.linear.weight.dtype)
            self.lora_A = None
            self.lora_B = None


def _get_target_modules() -> list[str]:
    return ["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj", "gate_proj"]


def apply_lora(
    model: nn.Module,
    r: int = 8,
    lora_alpha: float = 16,
    lora_dropout: float = 0.0,
    target_modules: list[str] | None = None,
    qlora: bool = False,
    bits: int = 4,
):
    if target_modules is None:
        target_modules = _get_target_modules()

    lora_cls = QLoRALinear if qlora else LoRALinear

    for name, module in list(model.named_modules()):
        if any(target in name for target in target_modules) and isinstance(module, nn.Linear):
            parent_name = name.rsplit(".", 1)[0]
            child_name = name.rsplit(".", 1)[-1]
            parent = model
            for part in parent_name.split("."):
                parent = getattr(parent, part)

            lora_module = lora_cls(
                module, r=r, lora_alpha=lora_alpha, lora_dropout=lora_dropout, bits=bits
            )
            setattr(parent, child_name, lora_module)

    return model


def merge_lora(model: nn.Module):
    for module in model.modules():
        if isinstance(module, (LoRALinear, QLoRALinear)):
            module.merge()
    return model


def _setup_distributed():
    if "RANK" not in os.environ or "WORLD_SIZE" not in os.environ:
        return False, 0, 1, None
    rank = int(os.environ.get("RANK", 0))
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    dist.init_process_group(backend="nccl" if torch.cuda.is_available() else "gloo")
    torch.cuda.set_device(local_rank)
    return True, rank, world_size, local_rank


def _cleanup_distributed():
    if dist.is_initialized():
        dist.destroy_process_group()


def _create_optimizer(model, config):
    optimizer_name = config.get("optimizer", "adamw").lower()
    lr = config.get("lora_lr", config.get("lr", 3e-4))
    weight_decay = config.get("weight_decay", 0.1)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    if not trainable_params:
        raise RuntimeError("No trainable parameters found. Ensure LoRA is applied.")

    if optimizer_name == "adafactor":
        return AdaFactor(
            trainable_params,
            lr=lr,
            beta1=config.get("adam_beta1", 0.0),
            beta2=config.get("adam_beta2", 0.999),
            weight_decay=weight_decay,
            clip_threshold=config.get("gradient_clip_norm", 1.0),
        )
    else:
        return torch.optim.AdamW(
            trainable_params,
            lr=lr,
            betas=(config.get("adam_beta1", 0.9), config.get("adam_beta2", 0.95)),
            weight_decay=weight_decay,
            eps=config.get("adam_eps", 1e-8),
        )


def _create_scheduler(optimizer, config, dataloader_len):
    scheduler_name = config.get("lr_scheduler", "cosine").lower()
    epochs = config.get("epochs", 1)
    warmup_ratio = config.get("warmup_ratio", 0.01)
    warmup_steps = config.get("warmup_steps", int(dataloader_len * epochs * warmup_ratio))

    if scheduler_name == "cosine":
        warmup = torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=0.1, end_factor=1.0, total_iters=warmup_steps
        )
        main = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=dataloader_len * epochs - warmup_steps,
            eta_min=config.get("min_lr", 1e-6),
        )
        return warmup, main
    elif scheduler_name == "linear":
        total_steps = dataloader_len * epochs
        return (
            torch.optim.lr_scheduler.LinearLR(
                optimizer, start_factor=1.0, end_factor=0.0, total_iters=total_steps
            ),
            None,
        )
    elif scheduler_name == "constant":
        return torch.optim.lr_scheduler.ConstantLR(optimizer, factor=1.0), None
    else:
        raise ValueError(f"Unsupported scheduler: {scheduler_name}")


def finetune(
    config_path="configs/config_4b.yaml",
    resume_from: str | None = None,
    lora: bool = True,
    qlora: bool = False,
    lora_r: int = 8,
    lora_alpha: float = 16,
    lora_dropout: float = 0.0,
    lora_target_modules: list[str] | None = None,
):
    config = load_config(config_path)

    is_distributed, rank, world_size, local_rank = _setup_distributed()
    device = get_device() if not is_distributed else f"cuda:{local_rank}"

    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    seed = config.get("seed", 42)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    log_dir = config.get("log_dir", "logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO if rank == 0 else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f"finetune_rank{rank}.log")),
            logging.StreamHandler(sys.stdout) if rank == 0 else logging.NullHandler(),
        ],
    )

    model = LLM(config).to(device)

    if lora or qlora:
        if rank == 0:
            print(f"Applying {'QLoRA' if qlora else 'LoRA'} with r={lora_r}, alpha={lora_alpha}")
        model = apply_lora(
            model,
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=lora_target_modules,
            qlora=qlora,
        )
        for name, param in model.named_parameters():
            if "lora_" not in name:
                param.requires_grad = False
    else:
        for param in model.parameters():
            param.requires_grad = True

    if is_distributed:
        model = DDP(
            model,
            device_ids=[local_rank] if torch.cuda.is_available() else None,
            find_unused_parameters=True,
        )

    if rank == 0:
        print(f"Parameters: {count_parameters(model):,}")
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Trainable parameters: {trainable:,}")

    tokenizer_path = config.get("tokenizer_path", "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}")
    tokenizer = load_tokenizer(tokenizer_path)
    pad_token_id = tokenizer.token_to_id("<pad>") or 0

    train_file = config.get("train_file", "data/train.jsonl")
    val_file = config.get("val_file", train_file)
    from ..training_data.prepare import InstructionCollator, InstructionDataset

    dataset = InstructionDataset(
        train_file, tokenizer, block_size=config.get("max_position_embeddings", 1024)
    )
    val_dataset = InstructionDataset(
        val_file, tokenizer, block_size=config.get("max_position_embeddings", 1024)
    )

    batch_size = config.get("batch_size", 1)
    num_workers = 0 if device == "cpu" else min(4, os.cpu_count() or 2)
    max_length = config.get("max_position_embeddings", 1024)

    if is_distributed:
        train_sampler = DistributedSampler(
            dataset, num_replicas=world_size, rank=rank, shuffle=True
        )
        val_sampler = DistributedSampler(
            val_dataset, num_replicas=world_size, rank=rank, shuffle=False
        )
        train_loader = DataLoader(
            dataset,
            batch_size=batch_size,
            sampler=train_sampler,
            num_workers=num_workers,
            pin_memory=(device == "cuda"),
            collate_fn=InstructionCollator(pad_token_id=pad_token_id, max_length=max_length),
            drop_last=True,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=max(1, batch_size // 2),
            sampler=val_sampler,
            num_workers=num_workers,
            pin_memory=(device == "cuda"),
            collate_fn=InstructionCollator(pad_token_id=pad_token_id, max_length=max_length),
            drop_last=False,
        )
    else:
        train_loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=(device == "cuda"),
            collate_fn=InstructionCollator(pad_token_id=pad_token_id, max_length=max_length),
            drop_last=True,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=max(1, batch_size // 2),
            shuffle=False,
            num_workers=num_workers,
            pin_memory=(device == "cuda"),
            collate_fn=InstructionCollator(pad_token_id=pad_token_id, max_length=max_length),
            drop_last=False,
        )

    optimizer = _create_optimizer(model, config)
    warmup_scheduler, main_scheduler = _create_scheduler(optimizer, config, len(train_loader))

    mixed_precision = config.get("mixed_precision", "fp16" if torch.cuda.is_available() else "none")
    use_cuda = torch.cuda.is_available()
    scaler = GradScaler(enabled=(mixed_precision == "fp16" and use_cuda))

    checkpoint_dir = config.get("checkpoint_dir", "checkpoints/finetune")
    os.makedirs(checkpoint_dir, exist_ok=True)
    latest_ckpt = os.path.join(checkpoint_dir, "latest.pt")
    best_ckpt = os.path.join(checkpoint_dir, "best.pt")

    start_epoch = 0
    best_val_loss = float("inf")
    global_step = 0

    if resume_from and os.path.exists(resume_from):
        start_epoch, best_val_loss = load_checkpoint(
            model, optimizer, warmup_scheduler, resume_from, device=device
        )
        if main_scheduler:
            with contextlib.suppress(Exception):
                main_scheduler.load_state_dict(optimizer.state_dict())
        print(f"Resumed from {resume_from} at epoch {start_epoch}")
    elif os.path.exists(latest_ckpt):
        start_epoch, best_val_loss = load_checkpoint(
            model, optimizer, warmup_scheduler, latest_ckpt, device=device
        )
        if main_scheduler:
            with contextlib.suppress(Exception):
                main_scheduler.load_state_dict(optimizer.state_dict())
        print(f"Resumed from {latest_ckpt} at epoch {start_epoch}")

    metrics_logger = MetricsLogger(log_dir, config.get("wandb_project"))
    train_metrics = TrainingMetrics()

    accumulation_steps = config.get("gradient_accumulation_steps", 1)
    gradient_clip = config.get("gradient_clip_norm", 1.0)
    checkpoint_every = config.get("checkpoint_every", 500)
    eval_every = config.get("eval_every", 500)
    max_train_steps = config.get("max_train_steps", None)
    gradient_checkpointing = config.get("gradient_checkpointing", True)

    model.train()

    try:
        for epoch in range(start_epoch, config.get("epochs", 1)):
            if is_distributed:
                train_sampler.set_epoch(epoch)

            total_loss = 0.0
            pbar = tqdm(train_loader, desc=f"Finetune Epoch {epoch + 1}", disable=(rank != 0))

            for i, batch in enumerate(pbar):
                input_ids = batch["input_ids"].to(device, non_blocking=True)
                labels = batch["labels"].to(device, non_blocking=True)

                if mixed_precision == "bf16":
                    with autocast(device_type="cuda", dtype=torch.bfloat16):
                        outputs = model(
                            input_ids,
                            labels=labels,
                            use_gradient_checkpointing=gradient_checkpointing,
                        )
                        loss = outputs["loss"] / accumulation_steps
                    loss.backward()
                elif mixed_precision == "fp16":
                    with autocast(device_type="cuda"):
                        outputs = model(
                            input_ids,
                            labels=labels,
                            use_gradient_checkpointing=gradient_checkpointing,
                        )
                        loss = outputs["loss"] / accumulation_steps
                    scaler.scale(loss).backward()
                else:
                    outputs = model(
                        input_ids, labels=labels, use_gradient_checkpointing=gradient_checkpointing
                    )
                    loss = outputs["loss"] / accumulation_steps
                    loss.backward()

                total_loss += loss.item() * accumulation_steps
                train_metrics.update(loss=loss.item() * accumulation_steps, tokens=labels.numel())

                if (i + 1) % accumulation_steps == 0:
                    if gradient_clip > 0:
                        if mixed_precision == "fp16":
                            scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip)

                    if mixed_precision == "fp16":
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        optimizer.step()

                    optimizer.zero_grad(set_to_none=True)

                    if warmup_scheduler:
                        warmup_scheduler.step()
                    if main_scheduler:
                        main_scheduler.step()

                    global_step += 1

                pbar.set_postfix(
                    {
                        "loss": f"{total_loss / (i + 1):.4f}",
                        "lr": f"{optimizer.param_groups[0]['lr']:.2e}",
                    }
                )

                if max_train_steps and global_step >= max_train_steps:
                    break

                if (i + 1) % eval_every == 0 or (i + 1) == len(train_loader):
                    val_metrics = evaluate_metrics(model, val_loader, device)
                    val_loss = val_metrics["loss"]
                    val_ppl = val_metrics["perplexity"]
                    val_acc = val_metrics["accuracy"]
                    model.train()

                    if rank == 0:
                        print(
                            f"Step {global_step} | Val loss: {val_loss:.4f} "
                            f"| Val ppl: {val_ppl:.2f} | Val acc: {val_acc:.4f}"
                        )
                        metrics_logger.log_metrics(
                            {
                                "val_loss": val_loss,
                                "val_perplexity": val_ppl,
                                "val_accuracy": val_acc,
                                "train_loss": total_loss / (i + 1),
                                "lr": optimizer.param_groups[0]["lr"],
                            },
                            global_step,
                        )

                    if val_loss < best_val_loss and rank == 0:
                        best_val_loss = val_loss
                        save_checkpoint(
                            model,
                            optimizer,
                            warmup_scheduler,
                            epoch,
                            best_val_loss,
                            best_ckpt,
                            config=config,
                            global_step=global_step,
                        )

                if (i + 1) % checkpoint_every == 0 and rank == 0:
                    save_checkpoint(
                        model,
                        optimizer,
                        warmup_scheduler,
                        epoch,
                        best_val_loss,
                        latest_ckpt,
                        config=config,
                        global_step=global_step,
                    )
                    remove_old_checkpoints(checkpoint_dir, keep_last_n=3)

            if rank == 0:
                save_checkpoint(
                    model,
                    optimizer,
                    warmup_scheduler,
                    epoch + 1,
                    best_val_loss,
                    latest_ckpt,
                    config=config,
                    global_step=global_step,
                )
                remove_old_checkpoints(checkpoint_dir, keep_last_n=3)

            if is_distributed:
                dist.barrier()

    except KeyboardInterrupt:
        if rank == 0:
            logger.info("Finetuning interrupted by user")
    finally:
        if is_distributed:
            _cleanup_distributed()

    if rank == 0:
        output_path = config.get("output_dir", "finetuned_model.pt")
        os.makedirs(
            os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True
        )

        unwrapped_model = model.module if is_distributed else model
        if lora or qlora:
            merge_lora(unwrapped_model)

        torch.save(unwrapped_model.state_dict(), output_path)
        print(f"Finetuned model saved to {output_path}")

        final_metrics = train_metrics.compute()
        logger.info(f"Final finetune metrics: {final_metrics}")
        metrics_logger.close()


if __name__ == "__main__":
    finetune()
