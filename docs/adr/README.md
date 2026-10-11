# Architecture Decision Records

Numbered in order. Status values: **proposed**, **accepted**, **superseded**,
**deprecated**.

## Why

Every non-obvious choice gets a record so it can be challenged later without
guessing. A decision is only traceable if the record still exists after the
code has changed around it.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-use-fastapi.md) | Use FastAPI for the API gateway | accepted |
| [0002](0002-postgresql-pgvector.md) | PostgreSQL + pgvector as the system of record | accepted |
| [0003](0003-redis-caching.md) | Redis for cache, rate limits and queues | accepted |
| [0004](0004-multi-model-routing.md) | Multi-model routing with a single provider interface | accepted |
| [0005](0005-websocket-scaling.md) | WebSocket scaling strategy | accepted |
| [0006](0006-quarantine-experimental-modules.md) | Quarantine experimental modules out of the product path | accepted |
| [0007](0007-pii-redaction-exclusions.md) | PII redaction excludes auth and identity endpoints | accepted |
| [0008](0008-https-redirect-preserves-method.md) | HTTPS redirect uses 307/308, never 301/302 | accepted |
| [0009](0009-single-auth-module.md) | One auth module; module/package shadowing removed | accepted |
| [0010](0010-test-environment-disables-tls-and-ip-allowlist.md) | Test environment disables TLS and IP enforcement | accepted |

## Template

See [template.md](template.md).

## Legacy records

`docs/ADR-001.md` … `docs/ADR-020.md` are the earlier flat-numbered records.
They are kept for history; new records go in this directory using the
zero-padded scheme above so ordering is stable.