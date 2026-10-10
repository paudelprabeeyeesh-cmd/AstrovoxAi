# Research Notes

This directory captures the research background behind the engine's design. Each
document links the implementation in `internal/` to the underlying theory.

| Topic | Implementation | Notes |
|---|---|---|
| [Operating Systems](os-internals.md) | `internal/runtime`, `internal/memory` | Scheduler and allocator design |
| [Database Internals](db-internals.md) | `internal/checkpoint`, `internal/pkg` | WAL, MVCC and index structures |
| [Linux Kernel](linux-kernel.md) | `internal/runtime` | Scheduling and memory-management analogues |
| [Compiler Theory](compiler-theory.md) | `internal/ir`, `internal/lang` | SSA, dataflow, codegen |
| Distributed Systems | `internal/distributed` | Consensus, replication, RPC |
| High-Performance Computing | `tensor/math`, `internal/benchmark` | Cache blocking, SIMD, NUMA |

Each note is intentionally short: what the subsystem does in Astrovox, the
classic design it follows, and where the code diverges.