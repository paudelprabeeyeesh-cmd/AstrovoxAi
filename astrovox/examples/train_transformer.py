"""Runnable examples: train a small transformer, then diagnose it.

Run with ``python -m astrovox.examples.train_transformer``. Everything here
uses only the public API, so it doubles as a check that the documented entry
points exist and work.
"""

from __future__ import annotations

import sys

import numpy as np

from astrovox.debug import (
    dashboard,
    format_consistency,
    gradient_consistency,
    propagation_trace,
    verify_updates,
    format_updates,
)
from astrovox.nlp import (
    CharTokenizer,
    LMConfig,
    LanguageModel,
    build_dataset,
    synthetic_corpus,
    train,
)
from astrovox.profile import count_backward_flops, count_flops
from astrovox.tensor.tensor import tensor


def example_train() -> dict:
    """Train a small causal language model and report the loss curve."""
    tokenizer = CharTokenizer()
    config = LMConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=64,
        num_layers=2,
        num_heads=4,
        num_kv_heads=2,
        d_ff=128,
        block_size=32,
        max_length=48,
        batch_size=8,
        learning_rate=3e-3,
        max_steps=100,
        warmup_steps=8,
        seed=0,
    )
    model = LanguageModel(config, tokenizer)
    parameters = sum(p.numel for p in model.parameters())
    print(f"trainable parameters: {parameters:,}")

    ids = tokenizer.encode(synthetic_corpus(documents=120, length=120))
    split = int(len(ids) * 0.9)
    train_data = build_dataset(tokenizer.decode(ids[:split]), tokenizer, config.block_size)
    val_data = build_dataset(tokenizer.decode(ids[split:]), tokenizer, config.block_size)
    print(f"train windows: {len(train_data)}   val windows: {len(val_data)}")

    result = train(model, train_data, val_data, steps=config.max_steps, log_every=20)
    print()
    for row in result["history"]:
        print(
            f"  step {row['step']:>4}  train {row['train_loss']:.4f}"
            f"  val {row['val_loss']:.4f}  ppl {row['ppl']:.2f}  lr {row['lr']:.2e}"
        )
    print()
    print(
        f"validation loss {result['initial_val_loss']:.4f} -> {result['final_val_loss']:.4f} "
        f"in {result['seconds']:.1f}s ({result['steps_per_second']:.2f} steps/s)"
    )

    print()
    batch_inputs, batch_targets = train_data.epoch(config.batch_size)[0]
    forward = count_flops(model.loss(tensor(batch_inputs), tensor(batch_targets)))
    backward_cost = count_backward_flops(model.loss(tensor(batch_inputs), tensor(batch_targets)))
    print(f"forward flops per batch: {forward.total:,}")
    print(f"backward flops per batch: {backward_cost.total:,}")
    print(f"most expensive: {forward.top(3)}")
    print()
    print(f"generated: {model.sample('the cat', max_new_tokens=60, seed=1)!r}")
    return result


def example_diagnose() -> None:
    """Check a model's autograd wiring and print the diagnostics."""
    tokenizer = CharTokenizer()
    config = LMConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=32,
        num_layers=2,
        num_heads=4,
        num_kv_heads=2,
        d_ff=64,
        block_size=16,
        max_length=32,
        batch_size=4,
        learning_rate=5e-3,
        max_steps=20,
        warmup_steps=3,
        seed=0,
    )
    model = LanguageModel(config, tokenizer)
    data = build_dataset(synthetic_corpus(documents=20, length=80), tokenizer, config.block_size)
    inputs, targets = data.epoch(4)[0]
    inputs = tensor(inputs)
    targets = tensor(targets)

    print("propagation trace:")
    print(propagation_trace(model.loss(inputs, targets)))
    print()

    # A tolerance of 1e-2 rather than 1e-3: the difference is taken in float32
    # through a chain of about forty operations, so the rounding noise of the
    # differencing itself reaches a few times 1e-3. Tightening this measures
    # the noise rather than the derivative.
    checks = gradient_consistency(lambda: model.loss(inputs, targets), model, threshold=1e-2)
    print("gradient consistency:")
    print(format_consistency(checks))
    print()

    print("dashboard:")
    print(dashboard(model.loss(inputs, targets), model, checks=checks).render())
    print()

    before = model.state_dict()
    model.train_step(inputs, targets)
    print("per-parameter updates:")
    print(format_updates(verify_updates(model, before)))


def main(argv: list[str] | None = None) -> int:
    """Run the examples named on the command line, or all of them."""
    argv = list(sys.argv[1:] if argv is None else argv)
    chosen = argv or ["train", "diagnose"]
    if "train" in chosen:
        print("=== training a small transformer ===")
        example_train()
    if "diagnose" in chosen:
        print()
        print("=== autograd diagnostics ===")
        example_diagnose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())