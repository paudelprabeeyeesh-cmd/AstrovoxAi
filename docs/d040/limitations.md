# D-040 Limitations

Honest list of what is not done or not verified. Nothing here is claimed
as working.

## Verification gaps

1. **Race detector not run.** `go test -race` requires cgo; this machine
   has no C compiler (`gcc` not on PATH). All concurrency tests pass
   uninstrumented. This is the largest open verification item and should
   be run in CI (the workflow exists).
2. **No extended fuzzing.** Fuzz seeds exist; no long `-fuzz` campaigns
   were run here.
3. **No profiles captured.** No CPU/memory/block profiles in this session.

## Capability gaps

4. **GPU/accelerator backends are simulation only.** No hardware was
   available; nothing may be described as hardware-verified. CPU is the
   verified backend.
5. **`internal/ir` optimization passes are inert stubs.** The real IR
   pipeline is `graph -> compiler TIR -> interpreter`.
6. **`internal/planner` cannot produce executable plans** (MTIR emits
   unimplemented opcodes). It is a memory planner, not an execution
   planner.
7. **No workflow engine, provider gateway, RAG, or multi-tenancy layer
   was added in this session.** Those come from the wider backlog
   (D-021..D-039); this work covered the D-040 core: tensors, autograd,
   models, training, checkpoints, the IR/compiler path, scheduling, and
   inference.
8. **Distributed coordination is untouched** (`internal/distributed` is a
   simulation; no consensus, no leases).

## Durability caveats

9. Checkpoint durability: data blocks are fsynced; the directory entry is
   fsynced best-effort. On filesystems without directory fsync, an
   immediate power loss after rename may lose the rename.
10. Model restore is exact-match: a checkpoint from a differently-shaped
    model is refused rather than partially applied (by design).

## Known risks

11. `math/rand`-based weight init is deterministic per Go toolchain, not
    across languages or guaranteed across future Go versions.
12. The inference executor caps concurrency with one global worker pool
    per executor; per-tenant quotas are not implemented (no tenant model
    in the Go core).
13. Concurrent model use is the caller's responsibility: modules have no
    internal locking (documented on the `Module` interface).
