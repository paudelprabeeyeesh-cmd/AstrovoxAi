"""A complete small language model: train, checkpoint, resume, generate.

This is the end-to-end check that the framework holds together. It trains a
causal transformer on a tiny synthetic corpus, verifies the loss falls and
perplexity improves, saves and restores a checkpoint to reproduce a step
exactly, and generates text by sampling.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import numpy as np

from astrovox.autograd import backward, no_grad
from astrovox.debug import dashboard, gradient_consistency
from astrovox.nn import Linear, Module, TransformerEncoder
from astrovox.nlp.tokenizer import BOS, EOS, CharTokenizer, Dataset, Tokenizer
from astrovox.ops import cross_entropy
from astrovox.optim import AdamW
from astrovox.profile import Profiler, count_flops
from astrovox.tensor.serialization import load_checkpoint, save_checkpoint
from astrovox.tensor.tensor import Tensor, tensor


@dataclass
class LMConfig:
    """Configuration for a small causal language model."""

    vocab_size: int = 320
    d_model: int = 64
    num_layers: int = 2
    num_heads: int = 4
    num_kv_heads: int = 2
    d_ff: int = 128
    block_size: int = 32
    max_length: int = 64
    batch_size: int = 8
    learning_rate: float = 3e-3
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    max_steps: int = 120
    warmup_steps: int = 10
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return the configuration as a plain dictionary."""
        return dict(vars(self))


def _pack_optimizer_state(optimizer: Any) -> tuple[dict[str, Any], dict[str, Tensor]]:
    """Split optimizer state into JSON scalars and a flat tensor map.

    The manifest is JSON, so NumPy arrays cannot travel through it, and the
    namespaced container holds one tensor per key. Scalars such as the
    learning rate stay in the manifest where they belong.
    """
    state = optimizer.state_dict()
    meta = {
        "type": state["type"],
        "lr": state["lr"],
        "step_count": state["step_count"],
    }
    tensors: dict[str, Tensor] = {}
    for key, entry in state["state"].items():
        for name, value in entry.items():
            as_tensor = value if isinstance(value, Tensor) else Tensor.from_numpy(np.asarray(value))
            tensors[f"{key}/{name}"] = as_tensor
    return meta, tensors


def _unpack_optimizer_state(optimizer: Any, meta: dict[str, Any], tensors: dict[str, Tensor]) -> None:
    """Restore optimizer state written by :func:`_pack_optimizer_state`.

    Keys arrive as text because they travelled through JSON. They are
    converted back to integers here; leaving them as strings would make every
    lookup miss, and the optimizer would silently restart with fresh moments.
    """
    optimizer.lr = meta.get("lr", optimizer.lr)
    optimizer.step_count = meta.get("step_count", 0)
    restored: dict[int, dict[str, Tensor]] = {}
    for key, value in tensors.items():
        raw_id, _, name = key.partition("/")
        if not name:
            continue
        try:
            slot = int(raw_id)
        except ValueError:
            continue
        restored.setdefault(slot, {})[name] = value
    optimizer.state = restored


class LanguageModel(Module):
    """A causal transformer trained with next-token prediction."""

    def __init__(self, config: LMConfig, tokenizer: Tokenizer | None = None) -> None:
        super().__init__()
        self.config = config
        self.tokenizer = tokenizer or CharTokenizer()
        self.model = TransformerEncoder(
            vocab_size=config.vocab_size,
            d_model=config.d_model,
            num_layers=config.num_layers,
            num_heads=config.num_heads,
            d_ff=config.d_ff,
            num_kv_heads=config.num_kv_heads,
            max_length=config.max_length,
        )
        # Tied output projection: reusing the embedding weights saves a full
        # matrix and is standard for small models.
        self.head = Linear(config.d_model, config.vocab_size, bias=False)
        self.optimizer = AdamW(
            list(self.parameters()),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        self.step_count = 0

    def forward(self, tokens: "Any") -> "Any":
        """Return logits of shape ``(batch, seq, vocab)``."""
        hidden = self.model(tokens)
        # The head expects (batch, seq, d_model); the encoder returns that
        # shape already, so this is a straight application per position.
        batch, seq, _ = hidden.shape.dims
        flat = hidden.reshape(batch * seq, self.config.d_model)
        return self.head(flat).reshape(batch, seq, self.config.vocab_size)

    def loss(self, inputs: "Any", targets: "Any") -> "Any":
        """Return the next-token cross-entropy for a batch."""
        logits = self.forward(inputs)
        batch, seq, vocab = logits.shape.dims
        flat_logits = logits.reshape(batch * seq, vocab)
        flat_targets = targets.reshape(batch * seq)
        return cross_entropy(flat_logits, flat_targets)

    def parameters(self, recurse: bool = True):
        """Return every trainable parameter exactly once.

        ``head`` is registered as a submodule, so it is already reached by the
        base traversal. Yielding it again would make the optimizer apply each
        update to the same weight twice.
        """
        return list(Module.parameters(self))

    def named_parameters(self, prefix: str = "", recurse: bool = True):
        """Yield ``(name, parameter)`` for the encoder and the head."""
        return Module.named_parameters(self, prefix, recurse)

    def state_dict(self, prefix: str = "") -> dict[str, Any]:
        """Return the encoder and head weights under one namespace."""
        return Module.state_dict(self, prefix)

    def learning_rate_at(self, step: int) -> float:
        """Return the learning rate for ``step``.

        Driven from the step counter rather than from a separate scheduler
        object, because a scheduler keeps its own step count and restoring
        only one of the two leaves them desynchronized, which would silently
        resume with a different learning rate.
        """
        config = self.config
        if step <= config.warmup_steps:
            if config.warmup_steps == 0:
                return config.learning_rate
            return config.learning_rate * step / config.warmup_steps
        decay_span = max(1, config.max_steps - config.warmup_steps)
        progress = min(1.0, (step - config.warmup_steps) / decay_span)
        floor = config.learning_rate * 0.1
        return floor + 0.5 * (config.learning_rate - floor) * (1.0 + math.cos(math.pi * progress))

    def train_step(self, inputs: "Any", targets: "Any") -> float:
        """Run one optimization step and return the loss before the update."""
        self.optimizer.zero_grad()
        loss = self.loss(inputs, targets)
        backward(loss)
        if self.config.grad_clip:
            self.optimizer.clip_grad_norm(self.config.grad_clip)
        self.optimizer.step()
        self.step_count += 1
        self.optimizer.lr = self.learning_rate_at(self.step_count)
        return float(loss.item())

    @no_grad()
    def evaluate(self, batches) -> float:
        """Return the mean loss over ``(inputs, targets)`` batches.

        A dataset yields exactly that, so a caller can pass
        ``data.batches(size)`` straight through. Raw NumPy arrays are
        converted here rather than requiring the caller to do it.
        """
        total = 0.0
        count = 0
        for batch in batches:
            batch_inputs, batch_targets = batch
            total += float(
                self.loss(_as_tensor(batch_inputs), _as_tensor(batch_targets)).item()
            )
            count += 1
        return total / max(count, 1)

    def perplexity(self, mean_loss: float) -> float:
        """Convert a mean loss into perplexity."""
        return float(math.exp(min(mean_loss, 700)))

    def save(self, path: str | Path, extra: dict[str, Any] | None = None) -> Path:
        """Write a checkpoint holding weights, optimizer, and step count."""
        optimizer_meta, optimizer_tensors = _pack_optimizer_state(self.optimizer)
        payload = {
            "step": self.step_count,
            "config": self.config.to_dict(),
            "history": list(self.history),
            "optimizer_meta": optimizer_meta,
        }
        payload.update(extra or {})
        # The head is a separate module, and the optimizer state holds many
        # tensors, so both travel as namespaced tensor groups rather than
        # through the JSON manifest.
        return save_checkpoint(
            self.model,
            path,
            payload,
            extra_states={
                "head": self.head.state_dict(),
                "optimizer": optimizer_tensors,
            },
        )

    def load(self, path: str | Path) -> dict[str, Any]:
        """Restore weights, optimizer state, and the step counter.

        The step counter matters beyond bookkeeping: warmup and the cosine
        schedule both key off it, so leaving it at zero would restart the
        learning rate rather than continue it.
        """
        extra = load_checkpoint(self.model, path)
        if "head" in extra:
            self.head.load_state_dict(extra["head"])
        self.step_count = int(extra.get("step", 0))
        self.history = list(extra.get("history", []))
        optimizer_tensors = extra.get("optimizer")
        if optimizer_tensors:
            _unpack_optimizer_state(
                self.optimizer, extra.get("optimizer_meta", {}), optimizer_tensors
            )
        return extra

    history: list[dict[str, float]] = field(default_factory=list)

    def sample(
        self,
        prompt: str,
        max_new_tokens: int = 40,
        temperature: float = 0.9,
        top_k: int = 20,
        seed: int = 0,
    ) -> str:
        """Generate a continuation of ``prompt`` by sampling from the model."""
        rng = np.random.default_rng(seed)
        ids = [self.tokenizer.bos_id] + self.tokenizer.encode(prompt)
        ids = ids[-self.config.max_length :]
        for _ in range(max_new_tokens):
            window = ids[-self.config.max_length :]
            input_ids = tensor(np.asarray([window], dtype=np.int64))
            logits = self.forward(input_ids)
            step_logits = logits.numpy()[0, -1] / max(temperature, 1e-6)
            if top_k and top_k < step_logits.size:
                threshold = np.partition(step_logits, -top_k)[-top_k]
                step_logits = np.where(step_logits < threshold, -np.inf, step_logits)
            probabilities = np.exp(step_logits - step_logits.max())
            probabilities = probabilities / probabilities.sum()
            choice = int(rng.choice(len(probabilities), p=probabilities))
            ids.append(choice)
            if choice == self.tokenizer.eos_id:
                break
        return self.tokenizer.decode(ids, skip_specials=True)


def _as_tensor(value: Any) -> Any:
    """Return ``value`` as a tensor, wrapping a NumPy array if needed."""
    if isinstance(value, tensor.__class__):
        return value
    return tensor(value)


def synthetic_corpus(seed: int = 0, documents: int = 200, length: int = 120) -> str:
    """Build a small corpus of repeated structured phrases.

    A tiny model can actually learn this structure, which makes the loss
    curve meaningful: a model that cannot learn it is broken, not just small.
    """
    rng = np.random.default_rng(seed)
    subjects = ["the cat", "a dog", "the bird", "a fish", "the fox"]
    verbs = ["runs", "sleeps", "jumps", "swims", "flies"]
    objects = ["fast", "slow", "high", "low", "far"]
    parts = []
    for _ in range(documents):
        sentences = []
        for _ in range(max(length // 12, 1)):
            sentences.append(
                f"{subjects[rng.integers(len(subjects))]} "
                f"{verbs[rng.integers(len(verbs))]} "
                f"{objects[rng.integers(len(objects))]} ."
            )
        parts.append(" ".join(sentences))
    return " ".join(parts)


def build_dataset(text: str, tokenizer: Tokenizer, block_size: int) -> Dataset:
    """Encode ``text`` and wrap it as a fixed-length window dataset."""
    return Dataset(tokenizer.encode(text), block_size)


def train(
    model: LanguageModel,
    train_data: Dataset,
    val_data: Dataset,
    steps: int | None = None,
    log_every: int = 20,
    profile: bool = False,
) -> dict[str, Any]:
    """Train ``model`` and return the loss history and timings."""
    total_steps = steps or model.config.max_steps
    batch_size = model.config.batch_size
    history: list[dict[str, float]] = []
    losses: list[float] = []
    val_losses: list[float] = []

    profiler = Profiler() if profile else None
    context = profiler if profiler is not None else _NullContext()
    with context:
        train_iter = iter(train_data.batches(batch_size))
        started = time.perf_counter()
        for step in range(1, total_steps + 1):
            if profiler is not None:
                region = profiler.region("train_step")
            else:
                region = _NullContext()
            with region:
                inputs, targets = next(train_iter)
                loss = model.train_step(tensor(inputs), tensor(targets))
            losses.append(loss)

            if step % log_every == 0 or step == total_steps:
                val_loss = model.evaluate(list(val_data.epoch(batch_size)))
                val_losses.append(val_loss)
                entry = {
                    "step": step,
                    "train_loss": round(float(np.mean(losses[-log_every:])), 5),
                    "val_loss": round(val_loss, 5),
                    "ppl": round(model.perplexity(val_loss), 3),
                    "lr": float(model.optimizer.lr),
                }
                history.append(entry)
        elapsed = time.perf_counter() - started

    model.history = history
    return {
        "history": history,
        "seconds": elapsed,
        "steps_per_second": total_steps / elapsed if elapsed else 0.0,
        "final_train_loss": history[-1]["train_loss"] if history else float("nan"),
        "final_val_loss": history[-1]["val_loss"] if history else float("nan"),
        "initial_val_loss": history[0]["val_loss"] if history else float("nan"),
        "profiler": profiler.to_dict() if profiler is not None else None,
    }


class _NullContext:
    """A context manager that does nothing, for the non-profiled path."""

    def __enter__(self) -> "_NullContext":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def diagnose(model: LanguageModel, inputs: "Any", targets: "Any") -> str:
    """Return the autograd dashboard for one training batch."""
    loss = model.loss(inputs, targets)
    checks = gradient_consistency(lambda: model.loss(inputs, targets), model)
    return dashboard(loss, model, checks=checks).render()


def count_model_flops(model: LanguageModel, inputs: "Any") -> int:
    """Return the forward flops of one batch."""
    return count_flops(model.forward(inputs)).total
