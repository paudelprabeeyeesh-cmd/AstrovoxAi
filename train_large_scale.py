#!/usr/bin/env python3
"""
Phase K Large-Scale Training CLI
=================================

Entry point for training 1B / 3.7B / 10B parameter models with:
- Distributed training (DDP, FSDP, ZeRO, TP, PP)
- Mixed precision (BF16 / FP16)
- Gradient and activation checkpointing
- Checkpoint save / resume
- Training report generation
- Model card generation

Usage examples:

    # Train 1B model with default settings
    python train_large_scale.py --model-size 1b

    # Train 3.7B with FSDP and BF16
    python train_large_scale.py --model-size 3.7b --strategy fsdp --mixed-precision bf16

    # Train 10B with ZeRO Stage 3 and gradient checkpointing
    python train_large_scale.py --model-size 10b --strategy zero3 --gradient-checkpointing

    # Resume from checkpoint
    python train_large_scale.py --model-size 1b --resume checkpoints/latest.pt

    # Multi-node / multi-GPU (via torchrun / SLURM)
    torchrun --nproc_per_node=4 train_large_scale.py --model-size 3.7b
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

# Ensure project root is on path for absolute imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.llm.training.large_scale import (
    MODEL_PRESETS,
    LargeScaleTrainer,
    TrainingConfig,
    train_large_scale,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="train_large_scale",
        description="Phase K Large-Scale LLM Training CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Model selection
    model_group = parser.add_argument_group("Model")
    model_group.add_argument(
        "--model-size",
        type=str,
        default="1b",
        choices=sorted(MODEL_PRESETS.keys()),
        help="Model size preset (1b, 3.7b, 10b)",
    )
    model_group.add_argument("--config", type=str, default=None, help="Path to YAML config file (overrides preset)")
    model_group.add_argument("--output-dir", type=str, default="output", help="Output directory for model and artifacts")

    # Data
    data_group = parser.add_argument_group("Data")
    data_group.add_argument("--train-file", type=str, default="data/train.txt", help="Training data path")
    data_group.add_argument("--val-file", type=str, default=None, help="Validation data path (optional)")
    data_group.add_argument("--val-ratio", type=float, default=0.05, help="Validation split ratio")
    data_group.add_argument("--tokenizer-path", type=str, default="tokenizer.json", help="Tokenizer path")

    # Training hyperparameters
    train_group = parser.add_argument_group("Training")
    train_group.add_argument("--epochs", type=int, default=None, help="Number of epochs")
    train_group.add_argument("--batch-size", type=int, default=None, help="Global batch size")
    train_group.add_argument("--gradient-accumulation-steps", type=int, default=None, help="Gradient accumulation steps")
    train_group.add_argument("--lr", type=float, default=None, help="Learning rate")
    train_group.add_argument("--weight-decay", type=float, default=None, help="Weight decay")
    train_group.add_argument("--grad-clip", type=float, default=None, help="Gradient clipping norm")
    train_group.add_argument("--warmup-steps", type=int, default=None, help="LR warmup steps")
    train_group.add_argument("--min-lr", type=float, default=None, help="Minimum learning rate")
    train_group.add_argument("--lr-scheduler", type=str, default=None, choices=["cosine", "linear", "onecycle", "constant", "step"])

    # Distributed
    dist_group = parser.add_argument_group("Distributed")
    dist_group.add_argument(
        "--strategy",
        type=str,
        default="ddp",
        choices=["ddp", "fsdp", "zero1", "zero2", "zero3", "tensor_parallel", "pipeline_parallel", "none"],
        help="Distributed training strategy",
    )
    dist_group.add_argument("--tensor-parallel-size", type=int, default=1, help="Tensor parallelism degree")
    dist_group.add_argument("--pipeline-parallel-size", type=int, default=1, help="Pipeline parallelism degree")
    dist_group.add_argument("--fsdp-sharding", type=str, default="FULL_SHARD", choices=["FULL_SHARD", "SHARD_GRAD_OP", "NO_SHARD"])
    dist_group.add_argument("--cpu-offload", action="store_true", default=None, help="Enable CPU offload (ZeRO / FSDP)")
    dist_group.add_argument("--find-unused-parameters", action="store_true", default=None, help="Find unused parameters in DDP")

    # Precision
    prec_group = parser.add_argument_group("Precision")
    prec_group.add_argument(
        "--mixed-precision",
        type=str,
        default=None,
        choices=["none", "fp16", "bf16", "amp"],
        help="Mixed precision mode",
    )

    # Checkpointing
    ckpt_group = parser.add_argument_group("Checkpointing")
    ckpt_group.add_argument("--resume", type=str, default=None, help="Resume from checkpoint path")
    ckpt_group.add_argument("--checkpoint-dir", type=str, default="checkpoints", help="Checkpoint directory")
    ckpt_group.add_argument("--checkpoint-interval", type=int, default=500, help="Checkpoint interval (steps)")
    ckpt_group.add_argument("--keep-last-n", type=int, default=3, help="Keep last N checkpoints")

    # Memory optimization
    mem_group = parser.add_argument_group("Memory Optimization")
    mem_group.add_argument("--gradient-checkpointing", action="store_true", default=None, help="Enable gradient checkpointing")
    mem_group.add_argument("--activation-checkpointing", action="store_true", default=None, help="Enable activation checkpointing")
    mem_group.add_argument("--activation-recompute", action="store_true", default=None, help="Enable activation recomputation")

    # Logging
    log_group = parser.add_argument_group("Logging")
    log_group.add_argument("--log-dir", type=str, default="logs", help="Log directory")
    log_group.add_argument("--experiment-name", type=str, default=None, help="Experiment name")
    log_group.add_argument("--seed", type=int, default=42, help="Random seed")

    # Hidden: local rank for torchrun
    parser.add_argument("--local_rank", type=int, default=int(os.environ.get("LOCAL_RANK", 0)), help=argparse.SUPPRESS)

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args


def args_to_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {}

    # Model
    if args.model_size:
        kwargs["model_size"] = args.model_size
    if args.config:
        kwargs["config_path"] = args.config
    if args.output_dir:
        kwargs["output_dir"] = args.output_dir

    # Data
    if args.train_file:
        kwargs["train_file"] = args.train_file
    if args.val_file:
        kwargs["val_file"] = args.val_file
    if args.val_ratio:
        kwargs["val_ratio"] = args.val_ratio
    if args.tokenizer_path:
        kwargs["tokenizer_path"] = args.tokenizer_path

    # Training
    if args.epochs is not None:
        kwargs["epochs"] = args.epochs
    if args.batch_size is not None:
        kwargs["batch_size"] = args.batch_size
    if args.gradient_accumulation_steps is not None:
        kwargs["gradient_accumulation_steps"] = args.gradient_accumulation_steps
    if args.lr is not None:
        kwargs["lr"] = args.lr
    if args.weight_decay is not None:
        kwargs["weight_decay"] = args.weight_decay
    if args.grad_clip is not None:
        kwargs["grad_clip"] = args.grad_clip
    if args.warmup_steps is not None:
        kwargs["warmup_steps"] = args.warmup_steps
    if args.min_lr is not None:
        kwargs["min_lr"] = args.min_lr
    if args.lr_scheduler is not None:
        kwargs["lr_scheduler"] = args.lr_scheduler

    # Distributed
    if args.strategy:
        kwargs["distributed"] = {"strategy": args.strategy}
        if args.tensor_parallel_size > 1:
            kwargs["distributed"]["tensor_parallel_size"] = args.tensor_parallel_size
        if args.pipeline_parallel_size > 1:
            kwargs["distributed"]["pipeline_parallel_size"] = args.pipeline_parallel_size
        if args.fsdp_sharding:
            kwargs["distributed"]["fsdp_sharding_strategy"] = args.fsdp_sharding
        if args.cpu_offload is not None:
            kwargs["distributed"]["cpu_offload"] = args.cpu_offload
        if args.find_unused_parameters is not None:
            kwargs["distributed"]["find_unused_parameters"] = args.find_unused_parameters

    # Precision
    if args.mixed_precision is not None:
        kwargs["precision"] = {"dtype": args.mixed_precision}

    # Checkpointing
    if args.checkpoint_dir:
        kwargs["checkpoint"] = {"dir": args.checkpoint_dir}
        if args.checkpoint_interval is not None:
            kwargs["checkpoint"]["interval"] = args.checkpoint_interval
        if args.keep_last_n is not None:
            kwargs["checkpoint"]["keep_last_n"] = args.keep_last_n

    # Memory
    if args.gradient_checkpointing is not None:
        kwargs["gradient_checkpointing"] = args.gradient_checkpointing
    if args.activation_checkpointing is not None:
        kwargs["activation_checkpointing"] = args.activation_checkpointing
    if args.activation_recompute is not None:
        kwargs["activation_recompute"] = args.activation_recompute

    # Logging
    if args.log_dir:
        kwargs["log_dir"] = args.log_dir
    if args.experiment_name:
        kwargs["experiment_name"] = args.experiment_name
    if args.seed is not None:
        kwargs["seed"] = args.seed

    return kwargs


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    kwargs = args_to_kwargs(args)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting large-scale training with args: %s", args)

    try:
        result = train_large_scale(
            model_size=args.model_size,
            config_path=args.config,
            resume_from=args.resume,
            **kwargs,
        )
        logger.info("Training completed successfully.")
        logger.info("Best validation loss: %.4f", result.get("best_val_loss", float("inf")))
        logger.info("Report: %s", result.get("report_path"))
        logger.info("Model card: %s", result.get("model_card_path"))
        return 0
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user.")
        return 130
    except Exception as exc:
        logger.error("Training failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
