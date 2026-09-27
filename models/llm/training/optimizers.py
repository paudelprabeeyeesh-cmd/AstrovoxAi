import logging
import math
import warnings
from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn as nn
from torch.optim import Optimizer
from torch.optim.lr_scheduler import (
    ConstantLR,
    CosineAnnealingLR,
    LinearLR,
    OneCycleLR,
    SequentialLR,
    StepLR,
    _LRScheduler,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gradient Clipping Utilities
# ---------------------------------------------------------------------------

def clip_grad_max_norm(
    model: nn.Module,
    max_norm: float,
    norm_type: float = 2.0,
) -> Optional[float]:
    total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm, norm_type=norm_type)
    return float(total_norm.item())


def clip_grad_value(model: nn.Module, clip_value: float) -> None:
    torch.nn.utils.clip_grad_value_(model.parameters(), clip_value)


def adaptive_grad_clip(
    model: nn.Module,
    clip_factor: float = 0.01,
    eps: float = 1e-3,
) -> Optional[float]:
    total_norm = 0.0
    for p in model.parameters():
        if p.grad is None:
            continue
        param_norm = p.data.norm(2)
        grad_norm = p.grad.data.norm(2)
        max_norm = clip_factor * param_norm + eps
        clip_coef = max_norm / (grad_norm + 1e-8)
        if clip_coef < 1.0:
            p.grad.data.mul_(clip_coef)
        total_norm += grad_norm.item() ** 2
    return math.sqrt(total_norm) if total_norm > 0 else 0.0


# ---------------------------------------------------------------------------
# Optimizers
# ---------------------------------------------------------------------------

def create_adamw(params, lr: float, weight_decay: float, betas: Tuple[float, float] = (0.9, 0.95)) -> Optimizer:
    return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay, betas=betas)


def create_adafactor(params, lr: float, weight_decay: float, **kwargs: Any) -> Optimizer:
    return torch.optim.AdaFactor(params, lr=lr, weight_decay=weight_decay, **kwargs)


def create_lion(params, lr: float, weight_decay: float, betas: Tuple[float, float] = (0.9, 0.99), **kwargs: Any) -> Optimizer:
    try:
        from lion_pytorch import Lion  # type: ignore
        return Lion(params, lr=lr, weight_decay=weight_decay, betas=betas, **kwargs)
    except ImportError:
        warnings.warn("lion_pytorch not installed; falling back to AdamW")
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay, betas=betas)


def create_sophia(params, lr: float, weight_decay: float, betas: Tuple[float, float] = (0.965, 0.99), rho: float = 0.04, **kwargs: Any) -> Optimizer:
    try:
        from Sophia import SophiaG  # type: ignore
        return SophiaG(params, lr=lr, betas=betas, rho=rho, weight_decay=weight_decay, **kwargs)
    except ImportError:
        warnings.warn("sophia optimizer not installed; falling back to AdamW")
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay, betas=betas)


def create_muon(params, lr: float, weight_decay: float, momentum: float = 0.9, **kwargs: Any) -> Optimizer:
    try:
        from muon import Muon  # type: ignore
        return Muon(params, lr=lr, momentum=momentum, weight_decay=weight_decay, **kwargs)
    except ImportError:
        warnings.warn("muon optimizer not installed; falling back to AdamW")
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)


def create_adamw_8bit(params, lr: float, weight_decay: float, betas: Tuple[float, float] = (0.9, 0.95), **kwargs: Any) -> Optimizer:
    try:
        import bitsandbytes as bnb  # type: ignore
        return bnb.optim.AdamW8bit(params, lr=lr, weight_decay=weight_decay, betas=betas, **kwargs)
    except ImportError:
        warnings.warn("bitsandbytes not installed; falling back to AdamW")
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay, betas=betas)


def create_paged_adamw(params, lr: float, weight_decay: float, betas: Tuple[float, float] = (0.9, 0.95), **kwargs: Any) -> Optimizer:
    try:
        import bitsandbytes as bnb  # type: ignore
        if hasattr(bnb.optim, "PagedAdamW8bit"):
            return bnb.optim.PagedAdamW8bit(params, lr=lr, weight_decay=weight_decay, betas=betas, **kwargs)
    except ImportError:
        pass
    warnings.warn("bitsandbytes paged optimizer not available; falling back to AdamW8bit or AdamW")
    try:
        import bitsandbytes as bnb  # type: ignore
        return bnb.optim.AdamW8bit(params, lr=lr, weight_decay=weight_decay, betas=betas, **kwargs)
    except ImportError:
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay, betas=betas)


_OPTIMIZER_BUILDERS: Dict[str, Any] = {
    "adamw": create_adamw,
    "adafactor": create_adafactor,
    "lion": create_lion,
    "sophia": create_sophia,
    "muon": create_muon,
    "adamw8bit": create_adamw_8bit,
    "adamw_8bit": create_adamw_8bit,
    "8bitadamw": create_adamw_8bit,
    "pagedadamw": create_paged_adamw,
    "paged_adamw": create_paged_adamw,
}


# ---------------------------------------------------------------------------
# LR Schedulers
# ---------------------------------------------------------------------------

def create_cosine_scheduler(
    optimizer: Optimizer,
    dataloader_len: int,
    epochs: int,
    warmup: int = 0,
    min_lr: float = 1e-6,
) -> _LRScheduler:
    if warmup > 0:
        return SequentialLR(
            optimizer,
            schedulers=[
                LinearLR(optimizer, start_factor=0.1, end_factor=1.0, total_iters=warmup),
                CosineAnnealingLR(optimizer, T_max=dataloader_len * epochs - warmup, eta_min=min_lr),
            ],
            milestones=[warmup],
        )
    return CosineAnnealingLR(optimizer, T_max=dataloader_len * epochs, eta_min=min_lr)


def create_one_cycle_scheduler(
    optimizer: Optimizer,
    dataloader_len: int,
    epochs: int,
    max_lr: float,
    pct_start: float = 0.3,
    div_factor: float = 25.0,
    final_div_factor: float = 1e4,
) -> _LRScheduler:
    total_steps = dataloader_len * epochs
    return OneCycleLR(
        optimizer,
        max_lr=max_lr,
        total_steps=total_steps,
        pct_start=pct_start,
        div_factor=div_factor,
        final_div_factor=final_div_factor,
        anneal_strategy="cos",
    )


def create_linear_scheduler(
    optimizer: Optimizer,
    dataloader_len: int,
    epochs: int,
) -> _LRScheduler:
    return LinearLR(optimizer, start_factor=1.0, end_factor=0.0, total_iters=dataloader_len * epochs)


def create_constant_scheduler(optimizer: Optimizer) -> _LRScheduler:
    return ConstantLR(optimizer, factor=1.0)


def create_step_decay_scheduler(
    optimizer: Optimizer,
    dataloader_len: int,
    epochs: int,
    step_size: int,
    gamma: float = 0.1,
) -> _LRScheduler:
    return StepLR(optimizer, step_size=step_size, gamma=gamma)


_SCHEDULER_BUILDERS: Dict[str, Any] = {
    "cosine": create_cosine_scheduler,
    "onecycle": create_one_cycle_scheduler,
    "one_cycle": create_one_cycle_scheduler,
    "linear": create_linear_scheduler,
    "constant": create_constant_scheduler,
    "step": create_step_decay_scheduler,
    "step_decay": create_step_decay_scheduler,
}


# ---------------------------------------------------------------------------
# Configuration Helper
# ---------------------------------------------------------------------------

class OptimizerSchedulerConfig:
    def __init__(self, config: Dict[str, Any], model: nn.Module, dataloader_len: int) -> None:
        self.config = config
        self.model = model
        self.dataloader_len = dataloader_len

    def build(self) -> Tuple[Optimizer, Optional[_LRScheduler]]:
        optimizer_name = str(self.config.get("optimizer", "adamw")).lower().replace("-", "").replace("_", "")
        builder = _OPTIMIZER_BUILDERS.get(optimizer_name)
        if builder is None:
            warnings.warn(f"Unknown optimizer '{optimizer_name}'; falling back to AdamW")
            builder = create_adamw
        lr = float(self.config.get("lr", 3e-4))
        weight_decay = float(self.config.get("weight_decay", 0.1))
        optimizer = builder(self.model.parameters(), lr=lr, weight_decay=weight_decay)

        scheduler_name = str(self.config.get("lr_scheduler", "cosine")).lower().replace("-", "").replace("_", "")
        scheduler_builder = _SCHEDULER_BUILDERS.get(scheduler_name)
        if scheduler_builder is None:
            warnings.warn(f"Unknown scheduler '{scheduler_name}'; falling back to cosine")
            scheduler_builder = create_cosine_scheduler
        epochs = int(self.config.get("epochs", 1))
        warmup = int(self.config.get("warmup_steps", max(1, int(self.dataloader_len * epochs * 0.01))))
        min_lr = float(self.config.get("min_lr", 1e-6))

        scheduler_kwargs: Dict[str, Any] = {
            "optimizer": optimizer,
            "dataloader_len": self.dataloader_len,
            "epochs": epochs,
            "warmup": warmup,
            "min_lr": min_lr,
        }
        if scheduler_name in ("onecycle", "one_cycle"):
            scheduler_kwargs["max_lr"] = lr
            scheduler_kwargs["pct_start"] = float(self.config.get("one_cycle_pct_start", 0.3))
            scheduler_kwargs["div_factor"] = float(self.config.get("one_cycle_div_factor", 25.0))
            scheduler_kwargs["final_div_factor"] = float(self.config.get("one_cycle_final_div_factor", 1e4))
            scheduler_kwargs.pop("warmup", None)
            scheduler_kwargs.pop("min_lr", None)
        elif scheduler_name in ("step", "step_decay"):
            scheduler_kwargs["step_size"] = int(self.config.get("step_size", max(1, self.dataloader_len * epochs // 3)))
            scheduler_kwargs["gamma"] = float(self.config.get("step_gamma", 0.1))
            scheduler_kwargs.pop("warmup", None)
            scheduler_kwargs.pop("min_lr", None)
        elif scheduler_name == "constant":
            scheduler_kwargs.pop("dataloader_len", None)
            scheduler_kwargs.pop("epochs", None)
            scheduler_kwargs.pop("warmup", None)
            scheduler_kwargs.pop("min_lr", None)
            optimizer_only = optimizer
            return optimizer, create_constant_scheduler(optimizer_only)

        scheduler = scheduler_builder(**scheduler_kwargs)
        return optimizer, scheduler


def get_optimizer_and_scheduler(
    config: Dict[str, Any],
    model: nn.Module,
    dataloader_len: int,
) -> Tuple[Optimizer, Optional[_LRScheduler]]:
    helper = OptimizerSchedulerConfig(config=config, model=model, dataloader_len=dataloader_len)
    return helper.build()
