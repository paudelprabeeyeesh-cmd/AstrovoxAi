from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

from models.llm.architectures.base import ArchitectureRegistry, BaseArchitecture
from models.llm.nas.search import ArchitectureGenome

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    score: float
    params: int
    memory_mb: float
    elapsed_seconds: float
    proxyloss: float = 0.0
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "params": self.params,
            "memory_mb": self.memory_mb,
            "elapsed_seconds": self.elapsed_seconds,
            "proxyloss": self.proxyloss,
            "error": self.error,
        }


class ArchitectureEvaluator:
    def __init__(
        self,
        device: str = "cpu",
        input_shape: tuple = (4, 32),
        vocab_size: int = 100,
        grad_steps: int = 2,
        skip_dropout: bool = True,
    ) -> None:
        self.device = torch.device(device)
        self.input_shape = input_shape
        self.vocab_size = vocab_size
        self.grad_steps = grad_steps
        self.skip_dropout = skip_dropout
        self.max_params: int = 100_000_000

    def evaluate(
        self, genome: ArchitectureGenome, device: Optional[str] = None
    ) -> tuple[float, int, float]:
        evalcache: Dict[str, tuple[float, int, float]] = {}
        return self.evaluate_batch([genome], device=device, cache=evalcache)[0]

    def evaluate_batch(
        self, genomes: List[ArchitectureGenome], device: Optional[str] = None, cache: Optional[Dict[str, Any]] = None
    ) -> List[tuple[float, int, float]]:
        results: List[tuple[float, int, float]] = []
        dev = device or str(self.device)
        if cache is None:
            cache = {}
        for genome in genomes:
            gid = genome.genome_id
            if gid in cache:
                results.append(cache[gid])
                continue
            result = self._evaluate_single(genome, dev)
            cache[gid] = result
            results.append(result)
        return results

    def _evaluate_single(self, genome: ArchitectureGenome, device: str) -> tuple[float, int, float]:
        start = time.time()
        errors = self._validate_genome(genome)
        if errors:
            logger.warning("Genome %s validation failed: %s", genome.genome_id, errors)
            return float("-inf"), 0, time.time() - start

        try:
            arch = ArchitectureRegistry.get(genome.architecture_family)
            if arch is None:
                logger.warning("Unknown architecture family: %s", genome.architecture_family)
                return float("-inf"), 0, time.time() - start

            config = self._build_eval_config(genome, arch)
            param_count = self._estimate_params(arch, config)
            if param_count > self.max_params:
                logger.warning("Genome %s has %d params, exceeding %d", genome.genome_id, param_count, self.max_params)
                return float("-inf"), param_count, time.time() - start

            proxy_loss = self._proxy_task_loss(arch, config, device)
            memory_mb = self._estimate_memory_mb(param_count)
            score = self._compute_score(proxy_loss, param_count, genome)
            elapsed = time.time() - start
            return score, param_count, elapsed

        except Exception as exc:
            logger.exception("Error evaluating genome %s", genome.genome_id)
            return float("-inf"), 0, time.time() - start

    def _validate_genome(self, genome: ArchitectureGenome) -> List[str]:
        errors = []
        if genome.hidden_size <= 0:
            errors.append(f"hidden_size must be positive, got {genome.hidden_size}")
        if genome.hidden_size % genome.num_heads != 0:
            errors.append(f"hidden_size={genome.hidden_size} must be divisible by num_heads={genome.num_heads}")
        if genome.num_layers <= 0:
            errors.append(f"num_layers must be positive, got {genome.num_layers}")
        if genome.intermediate_size <= 0:
            errors.append(f"intermediate_size must be positive, got {genome.intermediate_size}")
        if genome.dropout < 0.0 or genome.dropout > 1.0:
            errors.append(f"dropout must be in [0, 1], got {genome.dropout}")
        if genome.vocab_size <= 0:
            errors.append(f"vocab_size must be positive, got {genome.vocab_size}")
        return errors

    def _build_eval_config(self, genome: ArchitectureGenome, arch: BaseArchitecture) -> Dict[str, Any]:
        return {
            "vocab_size": self.vocab_size,
            "hidden_size": genome.hidden_size,
            "num_layers": genome.num_layers,
            "num_heads": genome.num_heads,
            "intermediate_size": genome.intermediate_size,
            "max_seq_len": genome.max_seq_len,
            "dropout": genome.dropout,
            "tie_weights": genome.tie_weights,
            "use_bias": genome.use_bias,
        }

    def _estimate_params(self, arch: BaseArchitecture, config: Dict[str, Any]) -> int:
        try:
            return arch.count_parameters(config)
        except Exception as exc:
            logger.warning("Error counting params: %s", exc)
            return self._fallback_param_count(config)

    def _fallback_param_count(self, config: Dict[str, Any]) -> int:
        hidden = config.get("hidden_size", 256)
        layers = config.get("num_layers", 4)
        heads = config.get("num_heads", 4)
        ffn = config.get("intermediate_size", 512)
        vocab = config.get("vocab_size", 100)
        use_bias = config.get("use_bias", False)
        use_rope = "rope_base" in config or config.get("use_rope", False)
        max_seq = config.get("max_seq_len", 1024)

        params = vocab * hidden
        params += max_seq * hidden
        per_block = 3 * layers * (hidden * hidden + (heads if use_bias else 0))
        per_block += layers * (hidden * ffn + ffn * hidden)
        per_block += 4 * layers * hidden
        if use_bias:
            per_block += 5 * layers * hidden
        params += per_block
        params += 2 * layers * hidden
        return params

    def _proxy_task_loss(
        self, arch: BaseArchitecture, config: Dict[str, Any], device: str
    ) -> float:
        torch.manual_seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)

        try:
            model = arch.build(config)
            model.eval()
            total_params = sum(p.numel() for p in model.parameters())
            if total_params > self.max_params:
                return float("inf")

            batch_size, seq_len = self.input_shape
            if total_params > 5_000_000:
                batch_size = max(1, batch_size // 2)
                seq_len = min(seq_len, config.get("max_seq_len", 512) // 2)

            input_ids = torch.randint(0, config.get("vocab_size", self.vocab_size), (batch_size, seq_len))
            input_ids = input_ids.to(device)

            dropout_init = config.get("dropout", 0.1)
            for module in model.modules():
                if isinstance(module, nn.Dropout):
                    module.p = 0.0
                    module.train()

            with torch.no_grad():
                try:
                    out = model(input_ids)
                    logits = out.get("logits", out)
                    loss = nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), input_ids.view(-1))
                except (RuntimeError, ValueError) as exc:
                    if "nan" in str(exc).lower() or "inf" in str(exc).lower():
                        return float("inf")
                    raise
            return float(loss.item())
        except Exception:
            raise
        finally:
            for module in model.modules():
                if isinstance(module, nn.Dropout):
                    module.p = dropout_init
                    module.train()

    def _estimate_memory_mb(self, param_count: int) -> float:
        return param_count * 4 / (1024 * 1024)

    def _compute_score(self, proxyloss: float, param_count: int, genome: ArchitectureGenome) -> float:
        if param_count == 0 or proxyloss <= 0 or not math.isfinite(proxyloss):
            return float("-inf")
        param_score = max(param_count, 1) / (1024 * 1024)
        base_score = 1.0 / proxyloss
        return base_score - 0.5 * math.log(param_score + 1)

    def performance_prediction(self, genome: ArchitectureGenome) -> Dict[str, Any]:
        arch = ArchitectureRegistry.get(genome.architecture_family)
        if arch is None:
            return {"error": f"Unknown architecture: {genome.architecture_family}"}
        config = self._build_eval_config(genome, arch)
        params = self._estimate_params(arch, config)
        return {
            "genome_id": genome.genome_id,
            "architecture_family": genome.architecture_family,
            "estimated_params": params,
            "estimated_memory_mb": self._estimate_memory_mb(params),
            "param_count_millions": params / 1_000_000,
            "intermediate_expansion": genome.intermediate_size / genome.hidden_size,
            "attention_heads": genome.num_heads,
            "heads_dim": genome.hidden_size // genome.num_heads if genome.num_heads > 0 else 0,
            "layers": genome.num_layers,
            "params_per_layer": params // genome.num_layers if genome.num_layers > 0 else 0,
        }

    def resource_estimation(self, genome: ArchitectureGenome) -> Dict[str, Any]:
        arch = ArchitectureRegistry.get(genome.architecture_family)
        if arch is None:
            return {"error": f"Unknown architecture: {genome.architecture_family}"}
        config = self._build_eval_config(genome, arch)
        params = self._estimate_params(arch, config)
        param_bytes = params * 4
        activation_mb = self._estimate_activation_mb(genome)
        total_mb = (param_bytes / (1024 * 1024)) + activation_mb
        return {
            "genome_id": genome.genome_id,
            "parameters": params,
            "param_bytes": param_bytes,
            "activation_mb": activation_mb,
            "total_mb": total_mb,
            "total_gb": total_mb / 1024,
            "dtype": "float32",
            "batch_size": self.input_shape[0],
            "seq_len": self.input_shape[1],
            "max_seq_len": genome.max_seq_len,
            "vocab_size": self.vocab_size,
            "note": "float32: 4 bytes per parameter, ~activation_mb per forward pass",
        }

    def _estimate_activation_mb(self, genome: ArchitectureGenome) -> float:
        batch, seq_len = self.input_shape
        hidden = genome.hidden_size
        layers = genome.num_layers
        bytes_per_elem = 4
        hidden_bytes = batch * seq_len * hidden * bytes_per_elem
        num_kv_heads = getattr(genome, "num_kv_heads", genome.num_heads)
        kv_hidden = batch * seq_len * num_kv_heads * (hidden // genome.num_heads) * 2
        total = hidden_bytes * layers + kv_hidden * layers
        return total / (1024 * 1024)
