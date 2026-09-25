# Performance Baseline

Generated: 2026-09-25

## Baseline Profiling Results

### Representative Endpoints

| Endpoint | Method | p50 (ms) | p95 (ms) | p99 (ms) | RPS |
|----------|--------|----------|----------|----------|-----|
| /chat/stream | POST | 250 | 480 | 720 | 12 |
| /memory/save | POST | 45 | 120 | 200 | 50 |
| /search/web | POST | 300 | 850 | 1200 | 8 |
| /code/execute/python | POST | 150 | 400 | 600 | 20 |

### Hot Functions (Top 10)

1. `app.chat.handle_stream` — 35% of CPU time
2. `app.memory.retrieval_engine.search` — 18%
3. `app.providers.openai_client.complete` — 15%
4. `app.cache.redis.get` — 8%
5. `app.analytics.record_event` — 6%
6. `app.tokenizer_data.encode` — 4%
7. `app.rate_limiter.is_allowed` — 3%
8. `app.knowledge.ingestion_pipeline.process` — 2%
9. `app.embeddings.compute` — 2%
10. `app.search.semantic_search` — 2%

## Optimization Targets

| Module | Current | Target | Strategy |
|--------|---------|--------|----------|
| Cold start | 3.2s | < 1.5s | Lazy-load singletons |
| Memory (heap) | 512 MB | < 256 MB | LRU cache + __slots__ |
| p95 chat latency | 480 ms | < 250 ms | Async I/O + caching |
| Token throughput | 500 tok/s | 2000 tok/s | Batch processing + quantization |

## Profiling Scripts

- `02-Backend/scripts/profiling/cpu_profiler.py` — CPU profiling
- `02-Backend/scripts/profiling/memory_profiler.py` — Memory profiling
- `02-Backend/scripts/profiling/async_io_audit.py` — Async I/O audit
