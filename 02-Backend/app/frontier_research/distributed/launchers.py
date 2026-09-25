"""Distributed training recipes and launchers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class DistributedConfig:
    num_nodes: int = 1
    num_gpus_per_node: int = 1
    backend: str = "nccl"
    master_addr: str = "localhost"
    master_port: str = "29500"
    rank: int = 0
    world_size: int = 1


class DistributedLauncher:
    def __init__(self, config: DistributedConfig | None = None):
        self.config = config or DistributedConfig()
        self.processes: list[Any] = []

    def launch(self, train_fn: Callable[[Any], Any], *args: Any, **kwargs: Any) -> list[Any]:
        if self.config.num_nodes <= 1 and self.config.num_gpus_per_node <= 1:
            return [train_fn(*args, **kwargs)]
        return self._launch_multi(train_fn, *args, **kwargs)

    def _launch_multi(self, train_fn: Any, *args: Any, **kwargs: Any) -> list[Any]:
        env = self._build_env()
        logger.info("Launching distributed training with env: %s", env)
        results = []
        for rank in range(self.config.world_size):
            try:
                result = train_fn(rank, *args, **kwargs)
                results.append(result)
            except Exception as exc:
                logger.error("Rank %d failed: %s", rank, exc)
        return results

    def _build_env(self) -> dict[str, str]:
        env = {
            "MASTER_ADDR": self.config.master_addr,
            "MASTER_PORT": self.config.master_port,
            "WORLD_SIZE": str(self.config.world_size),
            "RANK": str(self.config.rank),
            "BACKEND": self.config.backend,
        }
        return env

    def cleanup(self) -> None:
        self.processes = []


class DeepSpeedLauncher:
    def __init__(self, config: DistributedConfig | None = None, ds_config: dict[str, Any] | None = None):
        self.config = config or DistributedConfig()
        self.ds_config = ds_config or {}

    def launch(self, train_fn: Any, *args: Any, **kwargs: Any) -> Any:
        env = self._build_env()
        logger.info("Launching DeepSpeed with config keys: %s", list(self.ds_config.keys()))
        return train_fn(self.ds_config, *args, **kwargs)

    def _build_env(self) -> dict[str, str]:
        return {
            "MASTER_ADDR": self.config.master_addr,
            "MASTER_PORT": self.config.master_port,
            "WORLD_SIZE": str(self.config.world_size),
            "RANK": str(self.config.rank),
        }


class FSDPLauncher:
    def __init__(self, config: DistributedConfig | None = None):
        self.config = config or DistributedConfig()

    def launch(self, train_fn: Any, *args: Any, **kwargs: Any) -> Any:
        env = self._build_env()
        logger.info("Launching FSDP training")
        return train_fn(*args, **kwargs)

    def _build_env(self) -> dict[str, str]:
        return {
            "MASTER_ADDR": self.config.master_addr,
            "MASTER_PORT": self.config.master_port,
            "WORLD_SIZE": str(self.config.world_size),
            "RANK": str(self.config.rank),
        }
