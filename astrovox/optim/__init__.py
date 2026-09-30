"""Optimizers and learning rate schedules."""

from astrovox.optim.adam import Adam, AdamW
from astrovox.optim.base import Optimizer
from astrovox.optim.lion import Lion
from astrovox.optim.scheduler import (
    ConstantLR,
    CosineAnnealingLR,
    ExponentialLR,
    LinearWarmupLR,
    LRScheduler,
    OneCycleLR,
    PlateauLR,
    StepLR,
    build_scheduler,
)
from astrovox.optim.sgd import SGD

__all__ = [
    "Adam",
    "AdamW",
    "ConstantLR",
    "CosineAnnealingLR",
    "ExponentialLR",
    "LRScheduler",
    "LinearWarmupLR",
    "Lion",
    "OneCycleLR",
    "Optimizer",
    "PlateauLR",
    "SGD",
    "StepLR",
    "build_scheduler",
]
