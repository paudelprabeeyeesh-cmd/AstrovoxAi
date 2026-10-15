# D-040 Model Format and Validation

## What exists

There is no external model-file loader (no ONNX/Safetensors importer in
the Go core; `internal/onnx` exists but is not wired into a load path).
What exists and is verified is the **checkpoint** format added in this
work, plus tensor serialization.

## Checkpoint format (`internal/checkpoint/file.go`)

```
[magic "AXCK"][u32 version][u32 headerLen][header JSON][payload][u64 CRC64]
```

- Header: version, model name, optional metadata, optional optimizer
  state, and a tensor table with name, shape, and element offset/length.
- Payload: little-endian IEEE-754 float64 per tensor, in name-sorted order
  (byte-deterministic output).
- Optimizer state: kind (e.g. "sgd", "adam"), step counter, per-parameter
  moment buffers.
- Validation on write: non-empty model name, unique names, positive dims,
  data length equals shape, optimizer moments reference real parameters.
- Validation on read: magic, version (mismatch is `CodeVersionMismatch`),
  header bounds, CRC64 (mismatch is `CodeCorruptData`), tensor ranges
  within payload, shape equals payload length. Truncated files fail closed.

## Restore rules (`model/persist.go`)

- A checkpoint must name exactly the model's parameters: extra, missing,
  or shape-mismatched entries are errors. Partial restores are refused.
- Restore loads into a model built with a *different* seed in the
  acceptance test and produces bit-identical outputs.

## Security posture

- No executable code is deserialized: the payload is numeric only.
- Files are read and written through `os` APIs with explicit temp+rename;
  no path construction from untrusted input is performed by this package.
  Callers must treat the path itself as trusted.
