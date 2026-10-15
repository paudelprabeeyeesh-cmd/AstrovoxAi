# D-040 Training and Checkpoints

## Training pipeline (verified end-to-end in the acceptance scenario)

```
dataset (deterministic tensors)
  -> model.MLP / model.Linear forward (no tape for inference, tape for training)
  -> model.MSELoss (Sub, Mul, Mean — all differentiable)
  -> Tape.Backward (gradients, finite-difference verified)
  -> autograd.SGD / autograd Adam step
  -> checkpoint.WriteFile (atomic, versioned, checksummed)
  -> RestoreFromCheckpoint (exact-match validation)
```

## Measured convergence

Deterministic task: fit `y = 2x - 0.5` on x in {-1, -0.5, 0, 0.5, 1} with
a 1->1 linear model, SGD lr=0.05, 400 steps:

- initial loss: 0.9253726451558313
- final loss: 1.0195948004863006e-18
- loss halves within a handful of steps and converges to machine
  precision; the acceptance test asserts `final < initial/2`.

This is a real optimizer updating real parameters on the real tensor
kernels — not a scripted trajectory.

## Optimizer semantics

- `Step` reads `Var.Grad`; variables without gradients are skipped.
- `ZeroGrad` clears gradients and momentum velocity.
- Documented and tested: a fresh tape per training step. Replaying a tape
  after `Step` is refused rather than differentiating stale values.

## Checkpoint guarantees

- **Atomicity**: temp file + fsync + rename; an interrupted write leaves
  the previous checkpoint intact and a partial temp file behind.
- **Integrity**: CRC64 over the whole body; a single flipped bit anywhere
  is refused.
- **Versioning**: the version is in the header and checked on read; a
  newer-format file is refused with `CodeVersionMismatch`.
- **Completeness**: restore requires an exact parameter-name match. There
  is no partial restore path.
- **Determinism**: identical state produces byte-identical files.

## Numerical safety

- Loss values are checked for finiteness by the tests; a non-finite loss
  fails the scenario rather than corrupting parameters silently.
- Gradients are finite-difference verified for every rule that claims
  support.
