# Research Notes — Database Internals

> Implementation anchors: `internal/checkpoint`, `internal/pkg`,
> `internal/rpc`, `internal/vectordb`, `internal/knowledge`.

## 1. Write-Ahead Logging

`internal/checkpoint` implements the durability half of WAL without the log
itself: every `Save` writes an immutable, content-addressed snapshot and
retains the last N versions (`MemoryStore.maxKept`).

| WAL property | Astrovox implementation |
|---|---|
| Append-only history | `Store.Versions()` ascending |
| Idempotent replay | `Sync` applies shards by name, order-independent |
| Corruption detection | FNV-1a shard hashes + `Verify()` |
| Point-in-time recovery | `Load(version)` |

The difference from a database WAL is intentional: training snapshots are large
and idempotent, so versioned snapshots plus hashing give the same
"apply to reach version V" semantics without replaying individual log records.

## 2. MVCC

Distributed training uses snapshot isolation by construction:

- Each checkpoint has a monotonically increasing version (`Coordinator.Save`).
- Workers read a consistent snapshot (`Sync`) and never observe partial updates.
- Writers publish new versions atomically; readers keep the old one until apply.

This matches MVCC's "readers see the version they started with" contract, with
the version number standing in for a transaction id.

## 3. Indexing

| DB structure | Astrovox analogue |
|---|---|
| B+ tree | `internal/vectordb` HNSW (ordered ANN) |
| Secondary index | `index.shard` map in `internal/checkpoint` |
| Hash index | `Vocabulary.tokenToID` in `internal/tokenizer` |
| Query planner | `Graph.Execute` in `internal/knowledge` |

## 4. Replication & Sharding

`internal/distributed` covers the two classic axes:

- **Sharding** — `data_parallel.go` partitions parameters across ranks (ZeRO).
- **Replication** — `tensor_parallel.go` shards a single tensor across ranks and
  `ProcessGroup` collectives reduce across the replicas.

Fault recovery (`internal/rpc` + coordinator rendezvous) plays the role of an
election/rejoin protocol: a lost worker triggers re-rendezvous and re-sync from
the latest snapshot rather than logical log shipping.