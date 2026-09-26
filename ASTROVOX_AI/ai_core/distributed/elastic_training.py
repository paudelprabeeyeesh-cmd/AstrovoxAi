"""Elastic training: fault-tolerant distributed training with torchrun integration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class ElasticConfig:
    min_nodes: int = 1
    max_nodes: int = 4
    gpus_per_node: int = 1
    master_addr: str = "localhost"
    master_port: str = "29500"
    elastic_timeout: int = 300
    rendezvous: str = "env://"


class ElasticTrainer:
    def __init__(self, model: nn.Module, optimizer: torch.optim.Optimizer, config: ElasticConfig):
        self.model = model
        self.optimizer = optimizer
        self.config = config
        self.world_size = int(os.environ.get("WORLD_SIZE", str(config.gpus_per_node * config.min_nodes)))
        self.rank = int(os.environ.get("RANK", "0"))
        self.local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        self.node_rank = self.rank // config.gpus_per_node
        self.checkpoint_dir = os.environ.get("ASTROVOX_CHECKPOINT_DIR", "/tmp/astrovox_checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self._init_distributed()

    def _init_distributed(self) -> None:
        if not dist.is_initialized():
            os.environ.setdefault("MASTER_ADDR", self.config.master_addr)
            os.environ.setdefault("MASTER_PORT", self.config.master_port)
            os.environ.setdefault("WORLD_SIZE", str(self.world_size))
            os.environ.setdefault("RANK", str(self.rank))
            dist.init_process_group(backend="nccl", timeout=torch.distributed.Timeout(self.config.elastic_timeout))
            torch.cuda.set_device(self.local_rank)

    def train_step(self, batch: Dict[str, torch.Tensor], loss_fn: Any) -> float:
        self.model.train()
        device = torch.device(f"cuda:{self.local_rank}")
        input_ids = batch["input_ids"].to(device)
        labels = batch.get("labels", input_ids).to(device)
        logits = self.model(input_ids)
        loss = loss_fn(logits.view(-1, logits.size(-1)), labels.view(-1))
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
        return loss.item()

    def save_checkpoint(self, step: int) -> str:
        if self.rank == 0:
            os.makedirs(self.checkpoint_dir, exist_ok=True)
        dist.barrier()
        path = os.path.join(self.checkpoint_dir, f"elastic_ckpt_step_{step}_rank_{self.rank}.pt")
        torch.save({"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict(), "step": step, "rank": self.rank, "world_size": self.world_size}, path)
        dist.barrier()
        return path

    def load_checkpoint(self, step: int) -> None:
        path = os.path.join(self.checkpoint_dir, f"elastic_ckpt_step_{step}_rank_{self.rank}.pt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        ckpt = torch.load(path, map_location=f"cuda:{self.local_rank}")
        self.model.load_state_dict(ckpt["model"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
        dist.barrier()
        logger.info("Loaded elastic checkpoint at step %d", step)

    def elastic_barrier(self) -> None:
        if dist.is_initialized():
            dist.barrier()

    def get_elastic_state(self) -> Dict[str, Any]:
        return {"world_size": self.world_size, "rank": self.rank, "node_rank": self.node_rank, "local_rank": self.local_rank}

    def cleanup(self) -> None:
        if dist.is_initialized():
            dist.destroy_process_group()
