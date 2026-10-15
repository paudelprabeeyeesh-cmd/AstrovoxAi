# D-040 Security Review (scope of this session)

## Threat surface touched

- Tensor op inputs (shapes, dtypes, sizes) — treated as untrusted.
- Checkpoint files — treated as untrusted.
- Inference requests (IDs, input counts, tensor sizes, deadlines) —
  treated as untrusted.
- Tool-call arguments in `internal/tools` — treated as untrusted
  (regression: approval gating fixed).

## Controls verified in this work

1. **Bounded allocation.** Tensor construction uses checked arithmetic;
   oversized shapes fail with typed errors. The inference executor
   enforces per-request input counts and element limits
   (`CodeResourceExhausted`) *before* admission.
2. **No executable content in persistence.** The checkpoint payload is
   numeric only; no code is deserialized.
3. **Fail-closed reads.** Corrupt, truncated, or wrong-version checkpoints
   are refused; a checksum mismatch is `CodeCorruptData`.
4. **Atomic writes.** Temp + fsync + rename prevents leaving a truncated
   file at the destination path.
5. **Authorization boundary.** Tool execution requires an approved
   decision, decided once and enforced by the executor; skips are
   classified so refusals cannot be misreported as capacity events.
   Denied-permission and malformed-argument cases have tests
   (`internal/tools/agent` suite).
6. **No secrets in artifacts.** No credentials exist in the code paths
   added; no test fixtures contain secrets. Logs emitted by the new code
   contain IDs and counters only.
7. **Explicit timeouts/cancellation.** Inference deadlines are enforced at
   submission and during execution; cancellation propagates into the
   model context.
8. **Backpressure.** The scheduler refuses overflow with a typed error
   rather than unbounded queue growth.

## Not covered here

- No authentication/authorization system was added (the Python backend
  has JWT/RBAC; out of scope for the Go mission).
- No encryption at rest for checkpoints (filesystem-level concern).
- Path-traversal review of checkpoint *paths* is the caller's
  responsibility; this package does not build paths from untrusted input.
- The Python backend secret handling was not audited in this session.

## Residual risks

- Race detector not run (see limitations.md) — concurrency findings are
  therefore uninstrumented.
- Simulation backends must never be mistaken for hardware-verified
  capability (documented in backend-contract.md).
