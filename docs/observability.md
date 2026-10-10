# Observability Configuration

## Metrics (internal/monitor)

The engine exposes a counter/gauge/histogram registry with Prometheus-style labels.

| Metric | Type | Meaning |
|---|---|---|
| `requests_total` | counter | inference requests handled |
| `errors_total` | counter | failed requests |
| `latency_seconds` | histogram | per-request latency |
| `batch_size` | gauge | current dynamic batch size |
| `memory_bytes` | gauge | live allocator bytes |
| `kv_cache_hits` | counter | KV cache hits |
| `kv_cache_misses` | counter | KV cache misses |

Scrape: `GET :9090/metrics`.

## Logging (internal/logger)

Structured logging with levels, controlled by `ASTROVOX_LOG_LEVEL`.

```json
{"level":"info","ts":"2026-10-10T00:00:00Z","msg":"predict","latency_ms":2.1,"batch":8}
```

Levels: `debug`, `info`, `warn`, `error`.

## Tracing (internal/benchmark/profile + internal/debugger)

- `astrovox profile` builds a pprof CPU/heap profile.
- The debugger records a per-node trace (`seq`, `node`, `duration_us`, `vars`) for
  worst-first analysis.

## Health checks

`astrovox doctor` verifies:
1. backend availability and dtype support,
2. tensor kernel self-tests (GEMM, softmax, layernorm),
3. memory allocator integrity,
4. KV cache capacity vs configured window.

## Alert rules

| Rule | Condition | Severity |
|---|---|---|
| HighErrorRate | `errors_total` +5/min | critical |
| HighLatency | p99 > 100ms for 5m | warning |
| MemoryPressure | `memory_bytes` > 90% of limit | critical |
| CacheMissRate | `kv_cache_misses` > 90% of gets | warning |

## Dashboard

`internal/monitor` renders an HTML dashboard at `:9090/` with component
health, live metrics, and the active alert list.
