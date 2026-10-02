"""Measure a full training step, for before/after comparison."""

import time

import numpy as np

from astrovox import tensor
from astrovox.autograd import backward
from astrovox.nlp import (
    CharTokenizer,
    LMConfig,
    LanguageModel,
    build_dataset,
    synthetic_corpus,
    train,
)

tokenizer = CharTokenizer()
config = LMConfig(
    vocab_size=tokenizer.vocab_size, d_model=256, num_layers=4, num_heads=8,
    num_kv_heads=4, d_ff=1024, block_size=64, max_length=128, batch_size=8,
    learning_rate=3e-3, max_steps=20, warmup_steps=3, seed=0,
)
model = LanguageModel(config, tokenizer)
parameters = sum(p.numel for p in model.parameters())

ids = tokenizer.encode(synthetic_corpus(documents=80, length=120))
split = int(len(ids) * 0.9)
train_data = build_dataset(tokenizer.decode(ids[:split]), tokenizer, config.block_size)
val_data = build_dataset(tokenizer.decode(ids[split:]), tokenizer, config.block_size)

# Warm up, then time a real step.
train(model, train_data, val_data, steps=2, log_every=100)
inputs, targets = next(train_data.batches(config.batch_size))

from astrovox.profile import count_backward_flops, count_flops

loss = model.loss(tensor(inputs), tensor(targets))
forward_flops = count_flops(loss).total
backward_flops = count_backward_flops(loss).total

samples = []
for _ in range(3):
    started = time.perf_counter()
    model.train_step(tensor(inputs), tensor(targets))
    samples.append(time.perf_counter() - started)
step = float(np.median(samples))

print(f"parameters        : {parameters:,}")
print(f"batch shape       : {inputs.shape}")
print(f"forward flops     : {forward_flops:,}")
print(f"backward flops    : {backward_flops:,}")
print(f"train step        : {step * 1e3:.1f} ms")
print(f"throughput        : {forward_flops / step / 1e9:.2f} GFLOP/s")
print(f"steps per second  : {1 / step:.2f}")

result = train(model, train_data, val_data, steps=20, log_every=10)
print()
for row in result["history"]:
    print(
        f"  step {row['step']:>3}  train {row['train_loss']:.4f}"
        f"  val {row['val_loss']:.4f}  ppl {row['ppl']:.2f}"
    )
