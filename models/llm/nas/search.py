from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import torch

from models.llm.architectures.base import ArchitectureRegistry, BaseArchitecture

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureGenome:
    genome_id: str = ""
    architecture_family: str = "gpt2"
    num_layers: int = 4
    hidden_size: int = 256
    num_heads: int = 4
    intermediate_size: int = 512
    max_seq_len: int = 1024
    dropout: float = 0.1
    tie_weights: bool = True
    use_bias: bool = True
    parent_ids: List[str] = field(default_factory=list)
    mutation: Optional[str] = None
    generation: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.genome_id:
            self.genome_id = (
                f"{self.architecture_family}_L{self.num_layers}_H{self.hidden_size}_"
                f"hd{self.num_heads}_ffn{self.intermediate_size}"
            )

    def fitness(self) -> float:
        return self.metadata.get("fitness", float("-inf"))

    def as_config(self) -> Dict[str, Any]:
        return {
            "architecture_family": self.architecture_family,
            "num_layers": self.num_layers,
            "hidden_size": self.hidden_size,
            "num_heads": self.num_heads,
            "intermediate_size": self.intermediate_size,
            "max_seq_len": self.max_seq_len,
            "dropout": self.dropout,
            "tie_weights": self.tie_weights,
            "use_bias": self.use_bias,
        }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> ArchitectureGenome:
        return cls(
            architecture_family=config.get("architecture_family", "gpt2"),
            num_layers=int(config.get("num_layers", 4)),
            hidden_size=int(config.get("hidden_size", 256)),
            num_heads=int(config.get("num_heads", 4)),
            intermediate_size=int(config.get("intermediate_size", 512)),
            max_seq_len=int(config.get("max_seq_len", 1024)),
            dropout=float(config.get("dropout", 0.1)),
            tie_weights=bool(config.get("tie_weights", True)),
            use_bias=bool(config.get("use_bias", True)),
        )

    def copy(self) -> ArchitectureGenome:
        return copy.copy(self)

    def __repr__(self) -> str:
        return (
            f"ArchitectureGenome(id={self.genome_id}, family={self.architecture_family}, "
            f"L={self.num_layers}, H={self.hidden_size}, heads={self.num_heads}, "
            f"ffn={self.intermediate_size}, fitness={self.fitness():.4f})"
        )


class NASSearchSpace:
    _SEED_ARCHITECTURES: Dict[str, Dict[str, Any]] = {
        "gpt2-small": {
            "architecture_family": "gpt2",
            "num_layers": 4,
            "hidden_size": 256,
            "num_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 512,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": True,
        },
        "gpt2-base": {
            "architecture_family": "gpt2",
            "num_layers": 6,
            "hidden_size": 512,
            "num_heads": 8,
            "intermediate_size": 2048,
            "max_seq_len": 1024,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": True,
        },
        "gpt2-medium": {
            "architecture_family": "gpt2",
            "num_layers": 8,
            "hidden_size": 768,
            "num_heads": 12,
            "intermediate_size": 3072,
            "max_seq_len": 1024,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": True,
        },
        "llama-mini": {
            "architecture_family": "llama",
            "num_layers": 4,
            "hidden_size": 256,
            "num_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 1024,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": False,
        },
        "llama-base": {
            "architecture_family": "llama",
            "num_layers": 6,
            "hidden_size": 512,
            "num_heads": 8,
            "intermediate_size": 2048,
            "max_seq_len": 2048,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": False,
        },
        "mistral-tiny": {
            "architecture_family": "mistral",
            "num_layers": 4,
            "hidden_size": 256,
            "num_heads": 4,
            "intermediate_size": 512,
            "max_seq_len": 1024,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": False,
        },
        "mistral-base": {
            "architecture_family": "mistral",
            "num_layers": 6,
            "hidden_size": 512,
            "num_heads": 8,
            "intermediate_size": 2048,
            "max_seq_len": 2048,
            "dropout": 0.1,
            "tie_weights": True,
            "use_bias": False,
        },
    }

    _HIDDEN_SIZE_OPTIONS: List[int] = [128, 256, 384, 512, 768, 1024]
    _NUM_HEADS_OPTIONS: List[int] = [2, 4, 6, 8, 12, 16]
    _INTERMEDIATE_SIZE_OPTIONS: List[int] = [256, 512, 768, 1024, 1536, 2048, 3072, 4096, 5120]
    _NUM_LAYERS_OPTIONS: List[int] = [2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16]
    _MAX_SEQ_LEN_OPTIONS: List[int] = [128, 256, 512, 1024, 2048, 4096]
    _DROPOUT_OPTIONS: List[float] = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3]
    _ARCHITECTURE_FAMILIES: List[str] = ["gpt2", "llama", "mistral"]

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._registered = list(self._SEED_ARCHITECTURES.keys())

    def list_seed_architectures(self) -> List[str]:
        return list(self._SEED_ARCHITECTURES.keys())

    def sample_genome(self, strategy: str = "random") -> ArchitectureGenome:
        if strategy == "random":
            return self._random_genome()
        if strategy == "seed":
            name = self.rng.choice(self.list_seed_architectures())
            config = dict(self._SEED_ARCHITECTURES[name])
            return ArchitectureGenome.from_config(config)
        raise ValueError(f"Unknown sampling strategy: {strategy!r}")

    def _random_genome(self) -> ArchitectureGenome:
        family = self.rng.choice(self._ARCHITECTURE_FAMILIES)
        num_layers = self.rng.choice(self._NUM_LAYERS_OPTIONS)
        hidden_size = self.rng.choice(self._HIDDEN_SIZE_OPTIONS)
        num_heads = self._pick_num_heads(hidden_size)
        intermediate_size = self._pick_intermediate_size(hidden_size)
        max_seq_len = self.rng.choice(self._MAX_SEQ_LEN_OPTIONS)
        dropout = self.rng.choice(self._DROPOUT_OPTIONS)
        tie_weights = self.rng.choice([True, False])
        use_bias = family == "gpt2"
        return ArchitectureGenome(
            architecture_family=family,
            num_layers=num_layers,
            hidden_size=hidden_size,
            num_heads=num_heads,
            intermediate_size=intermediate_size,
            max_seq_len=max_seq_len,
            dropout=dropout,
            tie_weights=tie_weights,
            use_bias=use_bias,
        )

    def _pick_num_heads(self, hidden_size: int) -> int:
        valid = [h for h in self._NUM_HEADS_OPTIONS if hidden_size % h == 0 and h <= hidden_size]
        if not valid:
            for h in [2, 4, 8, 12, 16]:
                if hidden_size % h == 0:
                    return h
            raise ValueError(f"Cannot factor hidden_size={hidden_size} for multi-head attention")
        return self.rng.choice(valid)

    def _pick_intermediate_size(self, hidden_size: int) -> int:
        if hidden_size < 256:
            return hidden_size * 2
        if hidden_size < 512:
            return hidden_size * 3
        return hidden_size * 4

    def mutate(self, genome: ArchitectureGenome) -> ArchitectureGenome:
        child = genome.copy()
        child.parent_ids = [genome.genome_id]
        child.mutation = None
        child.metadata = {}

        mutation_ops = [
            self._mutate_num_layers,
            self._mutate_hidden_size,
            self._mutate_num_heads,
            self._mutate_intermediate_size,
            self._mutate_max_seq_len,
            self._mutate_dropout,
            self._mutate_tie_weights,
            self._mutate_architecture_family,
        ]
        op = self.rng.choice(mutation_ops)
        op_name = op.__name__
        if op(child):
            child.mutation = op_name
            return child
        child.mutation = "identity"
        return child

    def _mutate_num_layers(self, child: ArchitectureGenome) -> bool:
        delta = self.rng.choice([-1, 1, -2, 2])
        new_val = child.num_layers + delta
        if new_val not in self._NUM_LAYERS_OPTIONS or new_val < 1:
            return False
        child.num_layers = new_val
        return True

    def _mutate_hidden_size(self, child: ArchitectureGenome) -> bool:
        idx = self._HIDDEN_SIZE_OPTIONS.index(child.hidden_size) if child.hidden_size in self._HIDDEN_SIZE_OPTIONS else -1
        if idx < 0:
            return False
        delta = self.rng.choice([-1, 1])
        new_idx = idx + delta
        if not 0 <= new_idx < len(self._HIDDEN_SIZE_OPTIONS):
            return False
        new_hidden = self._HIDDEN_SIZE_OPTIONS[new_idx]
        if new_hidden % child.num_heads != 0:
            return False
        child.hidden_size = new_hidden
        if child.intermediate_size % new_hidden != 0:
            child.intermediate_size = self._pick_intermediate_size(new_hidden)
        return True

    def _mutate_num_heads(self, child: ArchitectureGenome) -> bool:
        if child.hidden_size % child.num_heads != 0:
            return False
        valid = [h for h in self._NUM_HEADS_OPTIONS if child.hidden_size % h == 0 and h <= child.hidden_size]
        if len(valid) <= 1:
            return False
        candidates = [h for h in valid if h != child.num_heads]
        if not candidates:
            return False
        child.num_heads = self.rng.choice(candidates)
        return True

    def _mutate_intermediate_size(self, child: ArchitectureGenome) -> bool:
        idx = self._INTERMEDIATE_SIZE_OPTIONS.index(child.intermediate_size) if child.intermediate_size in self._INTERMEDIATE_SIZE_OPTIONS else -1
        if idx < 0:
            return False
        delta = self.rng.choice([-1, 1])
        new_idx = idx + delta
        if not 0 <= new_idx < len(self._INTERMEDIATE_SIZE_OPTIONS):
            return False
        child.intermediate_size = self._INTERMEDIATE_SIZE_OPTIONS[new_idx]
        return True

    def _mutate_max_seq_len(self, child: ArchitectureGenome) -> bool:
        idx = self._MAX_SEQ_LEN_OPTIONS.index(child.max_seq_len) if child.max_seq_len in self._MAX_SEQ_LEN_OPTIONS else -1
        if idx < 0:
            return False
        delta = self.rng.choice([-1, 1])
        new_idx = idx + delta
        if not 0 <= new_idx < len(self._MAX_SEQ_LEN_OPTIONS):
            return False
        child.max_seq_len = self._MAX_SEQ_LEN_OPTIONS[new_idx]
        return True

    def _mutate_dropout(self, child: ArchitectureGenome) -> bool:
        idx = self._DROPOUT_OPTIONS.index(child.dropout) if child.dropout in self._DROPOUT_OPTIONS else -1
        if idx < 0:
            return False
        delta = self.rng.choice([-1, 1])
        new_idx = idx + delta
        if not 0 <= new_idx < len(self._DROPOUT_OPTIONS):
            return False
        child.dropout = self._DROPOUT_OPTIONS[new_idx]
        return True

    def _mutate_tie_weights(self, child: ArchitectureGenome) -> bool:
        child.tie_weights = not child.tie_weights
        return True

    def _mutate_architecture_family(self, child: ArchitectureGenome) -> bool:
        candidates = [f for f in self._ARCHITECTURE_FAMILIES if f != child.architecture_family]
        if not candidates:
            return False
        child.architecture_family = self.rng.choice(candidates)
        return True

    def crossover(
        self, parent_a: ArchitectureGenome, parent_b: ArchitectureGenome
    ) -> ArchitectureGenome:
        if parent_a.genome_id == parent_b.genome_id:
            return self.mutate(parent_a)

        strategy = self.rng.choice(["uniform", "block_layer", "block_attention"])
        child = ArchitectureGenome(
            parent_ids=[parent_a.genome_id, parent_b.genome_id],
            mutation="crossover",
            generation=max(parent_a.generation, parent_b.generation) + 1,
        )

        if strategy == "uniform":
            child.architecture_family = self.rng.choice([parent_a.architecture_family, parent_b.architecture_family])
            child.num_layers = self.rng.choice([parent_a.num_layers, parent_b.num_layers])
            child.hidden_size = self.rng.choice([parent_a.hidden_size, parent_b.hidden_size])
            child.num_heads = self.rng.choice([parent_a.num_heads, parent_b.num_heads])
            child.intermediate_size = self.rng.choice([parent_a.intermediate_size, parent_b.intermediate_size])
            child.max_seq_len = self.rng.choice([parent_a.max_seq_len, parent_b.max_seq_len])
            child.dropout = self.rng.choice([parent_a.dropout, parent_b.dropout])
            child.tie_weights = self.rng.choice([parent_a.tie_weights, parent_b.tie_weights])
            child.use_bias = parent_a.use_bias if child.architecture_family == "gpt2" else parent_b.use_bias

        elif strategy == "block_layer":
            child.architecture_family = self.rng.choice([parent_a.architecture_family, parent_b.architecture_family])
            child.hidden_size = parent_a.hidden_size if parent_a.num_layers >= parent_b.num_layers else parent_b.hidden_size
            child.num_layers = max(parent_a.num_layers, parent_b.num_layers)
            child.num_heads = parent_b.num_heads if self.rng.random() < 0.5 else parent_a.num_heads
            child.intermediate_size = parent_a.intermediate_size if parent_a.num_layers >= parent_b.num_layers else parent_b.intermediate_size
            child.max_seq_len = max(parent_a.max_seq_len, parent_b.max_seq_len)
            child.dropout = (parent_a.dropout + parent_b.dropout) / 2
            child.tie_weights = self.rng.choice([parent_a.tie_weights, parent_b.tie_weights])
            child.use_bias = child.architecture_family == "gpt2"

        else:
            child.architecture_family = self.rng.choice([parent_a.architecture_family, parent_b.architecture_family])
            child.num_layers = (parent_a.num_layers + parent_b.num_layers) // 2
            child.hidden_size = parent_b.hidden_size if self.rng.random() < 0.5 else parent_a.hidden_size
            child.num_heads = parent_b.num_heads if parent_b.hidden_size >= parent_a.hidden_size else parent_a.num_heads
            child.intermediate_size = parent_b.intermediate_size if parent_b.hidden_size >= parent_a.hidden_size else parent_a.intermediate_size
            child.max_seq_len = max(parent_a.max_seq_len, parent_b.max_seq_len)
            child.dropout = self.rng.choice([parent_a.dropout, parent_b.dropout])
            child.tie_weights = self.rng.choice([parent_a.tie_weights, parent_b.tie_weights])
            child.use_bias = child.architecture_family == "gpt2"

        if child.hidden_size % child.num_heads != 0:
            valid = [h for h in self._NUM_HEADS_OPTIONS if child.hidden_size % h == 0 and h <= child.hidden_size]
            if valid:
                child.num_heads = self.rng.choice(valid)

        if child.hidden_size >= 512 and child.intermediate_size < 1024:
            child.intermediate_size = self._pick_intermediate_size(child.hidden_size)

        child.genome_id = (
            f"{child.architecture_family}_L{child.num_layers}_H{child.hidden_size}_"
            f"hd{child.num_heads}_ffn{child.intermediate_size}"
        )
        child.metadata = {}
        return child

    def get_seed_genomes(self) -> List[ArchitectureGenome]:
        return [ArchitectureGenome.from_config(dict(cfg)) for cfg in self._SEED_ARCHITECTURES.values()]

    def validate_genome(self, genome: ArchitectureGenome) -> List[str]:
        errors: List[str] = []
        arch = ArchitectureRegistry.get(genome.architecture_family)
        if arch is None:
            errors.append(f"Unknown architecture family: {genome.architecture_family}")
        if genome.hidden_size <= 0:
            errors.append(f"hidden_size must be positive, got {genome.hidden_size}")
        if genome.hidden_size % genome.num_heads != 0:
            errors.append(f"hidden_size={genome.hidden_size} must be divisible by num_heads={genome.num_heads}")
        if genome.num_layers <= 0:
            errors.append(f"num_layers must be positive, got {genome.num_layers}")
        if genome.intermediate_size <= 0:
            errors.append(f"intermediate_size must be positive, got {genome.intermediate_size}")
        if not 0.0 <= genome.dropout <= 1.0:
            errors.append(f"dropout must be in [0, 1], got {genome.dropout}")
        return errors
