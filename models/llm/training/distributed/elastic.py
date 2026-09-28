"""Elastic training support: node failure detection and automatic recovery."""

from __future__ import annotations

import contextlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import torch
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class ElasticConfig:
    """Configuration for elastic training."""

    min_nodes: int = 1
    max_nodes: int = 8
    node_failure_timeout: float = 60.0
    health_check_interval: float = 10.0
    auto_recovery: bool = True
    max_recovery_attempts: int = 5


@dataclass
class NodeState:
    """Tracks the state of a single cluster node."""

    rank: int
    hostname: str
    last_heartbeat: float = field(default_factory=time.time)
    alive: bool = True
    failure_count: int = 0


class FailureDetector:
    """Monitors node health via periodic heartbeats."""

    def __init__(self, config: ElasticConfig) -> None:
        self.config = config
        self._nodes: dict[int, NodeState] = {}
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: threading.Thread | None = None
        self._on_failure_callback: Any = None

    def register_node(self, rank: int, hostname: str) -> None:
        with self._lock:
            self._nodes[rank] = NodeState(rank=rank, hostname=hostname)

    def heartbeat(self, rank: int) -> None:
        with self._lock:
            if rank in self._nodes:
                self._nodes[rank].last_heartbeat = time.time()
                self._nodes[rank].alive = True
                self._nodes[rank].failure_count = 0

    def on_failure(self, callback: Any) -> None:
        self._on_failure_callback = callback

    def start(self) -> None:
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Failure detector started.")

    def stop(self) -> None:
        self._running = False
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Failure detector stopped.")

    def _monitor_loop(self) -> None:
        while self._running:
            time.sleep(self.config.health_check_interval)
            self._check_nodes()

    def _check_nodes(self) -> None:
        now = time.time()
        with self._lock:
            for rank, node in list(self._nodes.items()):
                if rank == dist.get_rank() if dist.is_initialized() else 0:
                    continue
                if now - node.last_heartbeat > self.config.node_failure_timeout:
                    node.alive = False
                    node.failure_count += 1
                    logger.warning("Node %d (rank=%d) marked as failed.", node.hostname, rank)
                    if self._on_failure_callback is not None:
                        try:
                            self._on_failure_callback(node)
                        except Exception as exc:
                            logger.error("Failure callback raised: %s", exc)


class ElasticTrainer:
    """Elastic training coordinator that handles node joins, failures, and recovery."""

    def __init__(self, config: ElasticConfig) -> None:
        self.config = config
        self._failure_detector = FailureDetector(config)
        self._recovery_attempts = 0
        self._checkpoint_dir = "elastic_checkpoints"
        self._current_step = 0

    def init(self) -> bool:
        try:
            if not dist.is_initialized():
                logger.warning("Process group not initialized; elastic features limited.")
                return False
            self._failure_detector.on_failure(self._handle_node_failure)
            self._failure_detector.start()
            logger.info(
                "Elastic trainer initialized: min_nodes=%d, max_nodes=%d",
                self.config.min_nodes,
                self.config.max_nodes,
            )
            return True
        except Exception as exc:
            logger.error("Failed to initialize elastic trainer: %s", exc)
            return False

    def _handle_node_failure(self, node: NodeState) -> None:
        if not self.config.auto_recovery:
            logger.info("Auto-recovery disabled; skipping recovery for failed node %d.", node.rank)
            return
        if self._recovery_attempts >= self.config.max_recovery_attempts:
            logger.error("Max recovery attempts reached; aborting.")
            return
        self._recovery_attempts += 1
        logger.warning(
            "Handling node failure (rank=%d, attempt=%d/%d).",
            node.rank,
            self._recovery_attempts,
            self.config.max_recovery_attempts,
        )
        if dist.is_initialized():
            try:
                dist.barrier()
            except Exception:
                pass

    def heartbeat(self) -> None:
        rank = dist.get_rank() if dist.is_initialized() else 0
        self._failure_detector.heartbeat(rank)

    def save_recovery_checkpoint(self, model: nn.Module, step: int) -> str:
        path = f"{self._checkpoint_dir}/recovery_ckpt_{step}.pt"
        os.makedirs(self._checkpoint_dir, exist_ok=True)
        torch.save(
            {"model": model.state_dict(), "step": step, "recovery_attempt": self._recovery_attempts},
            path,
        )
        logger.info("Recovery checkpoint saved: %s", path)
        return path

    def load_recovery_checkpoint(self, model: nn.Module, path: str) -> int:
        state = torch.load(path, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model"])
        self._current_step = state.get("step", 0)
        self._recovery_attempts = state.get("recovery_attempt", 0)
        logger.info("Recovery checkpoint loaded from %s (step=%d).", path, self._current_step)
        return self._current_step

    def cleanup(self) -> None:
        self._failure_detector.stop()
        if dist.is_initialized():
            with contextlib.suppress(Exception):
                dist.destroy_process_group()
