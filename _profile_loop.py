"""Profile a real training step to find where the time actually goes."""

import cProfile
import pstats
import io
import time

import numpy as np

from astrovox import tensor
from astrovox.autograd import backward
from astrovox.nn import Linear, ReLU, Sequential, TransformerEncoder
from astrovox.ops import cross_entropy
from astrovox.optim import AdamW
from astrovox.profile import count_flops

rng = np.random.default_rng(0)


def timed(fn, calls=3):
    for _ in range(1):
        fn()
    start = time.perf_counter()
    for _ in range(calls):
        fn()
    return (time.perf_counter() - start) / calls


print("=== isolate: raw numpy matmul vs Linear.forward vs full step ===")
x_small = rng.standard_normal((8, 256)).astype(np.float32)
lin = Linear(256, 512)
w_np = lin.weight.numpy()
x_np = x_small

t_matmul = timed(lambda: x_np @ w_np.T, 20)
t_linear = timed(lambda: lin(tensor(x_small)), 20)
print(f"  numpy x @ W.T            : {t_matmul * 1e3:8.3f} ms")
print(f"  Linear.forward (module)   : {t_linear * 1e3:8.3f} ms")
print(f"  overhead                  : {(t_linear - t_matmul) * 1e3:8.3f} ms"
      f"  ({100 * (t_linear - t_matmul) / t_linear:.0f}% of the layer)")

print()
print("=== the transposed weight copy, isolated ===")
t_transpose = timed(lambda: lin.weight.numpy().T.copy(), 50)
print(f"  weight.T copy (512x256)   : {t_transpose * 1e3:8.3f} ms")
t_nocopy = timed(lambda: x_np @ w_np.T, 50)
print(f"  matmul without that copy  : {t_nocopy * 1e3:8.3f} ms")
print(f"  so the copy is            : {100 * t_transpose / (t_nocopy + t_transpose):5.1f}% of a layer")

print()
print("=== graph construction vs execution, transformer forward ===")
enc = TransformerEncoder(320, 256, 4, 8, d_ff=1024, num_kv_heads=4, max_length=128)
tokens = tensor(rng.integers(0, 320, (8, 128)).astype(np.int64))
t_forward = timed(lambda: enc(tokens), 3)
with_forward = t_forward
from astrovox.autograd import no_grad

with no_grad():
    t_inference = timed(lambda: enc(tokens), 3)
print(f"  forward (graph on)        : {with_forward * 1e3:8.2f} ms")
print(f"  forward (no_grad)         : {t_inference * 1e3:8.2f} ms")
print(f"  graph overhead            : {(with_forward - t_inference) * 1e3:8.2f} ms"
      f"  ({100 * (with_forward - t_inference) / with_forward:.0f}%)")
print(f"  flops per forward         : {count_flops(enc(tokens).sum()).total:,}")
print(f"  achieved GFLOP/s           : "
      f"{count_flops(enc(tokens).sum()).total / with_forward / 1e9:.2f}")

print()
print("=== where the graph time goes (cProfile on 3 forwards) ===")
pr = cProfile.Profile()
pr.enable()
for _ in range(3):
    out = enc(tokens)
    out.sum().item()
pr.disable()
stream = io.StringIO()
pstats.Stats(pr, stream=stream).sort_stats("tottime").print_stats(14)
for line in stream.getvalue().splitlines()[4:24]:
    print(" ", line)

print("=== full training step (transformer LM) ===")
head = Linear(256, 320, bias=False)
opt = AdamW(list(enc.parameters()) + list(head.parameters()), lr=1e-4)
targets = tensor(rng.integers(0, 320, (8, 128)).astype(np.int64))
hidden = enc(tokens)
flat = hidden.reshape(8 * 128, 256)
logits = head(flat).reshape(8, 128, 320)
flat_targets = targets.reshape(8 * 128)


def full_step():
    opt.zero_grad()
    loss = cross_entropy(logits.reshape(8 * 128, 320), flat_targets)
    backward(loss)
    opt.step()


t_step = timed(full_step, 3)
print(f"  full train step           : {t_step * 1e3:8.2f} ms")
print(f"  forward alone             : {with_forward * 1e3:8.2f} ms")
print(f"  backward + optimizer      : {(t_step - with_forward) * 1e3:8.2f} ms")
