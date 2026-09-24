# Performance Tuning

## Profiling First

- Use Py-Spy or `cProfile` to identify CPU bottlenecks before optimizing.
- Use `memory_profiler` for memory-heavy workloads (embedding batches, graph traversals).
- Check `/metrics` (Prometheus) and Jaeger traces for latency outliers.

## Async & Concurrency

- Use `async/await` for I/O-bound operations (database, Redis, HTTP calls to LLM providers).
- Avoid blocking calls in async routes; offload CPU-bound work to thread or process pools.
- Tune `uvicorn` workers: `--workers N` (start with `2 * CPUs + 1`); use `--loop uvloop` for faster event loop.

## Database

- Index frequently queried columns in Postgres; use `EXPLAIN ANALYZE` to validate.
- Use `pgvector` indexes (`ivfflat` or `hnsw`) for embedding similarity search.
- Connection pool: size based on max connections / number of workers; avoid over-provisioning.
- Use read replicas for read-heavy workloads.

## Caching

- Cache frequent, deterministic responses in Redis (`caching/` module).
- Use semantic caching for LLM responses with similarity thresholds.
- Set TTLs based on data freshness requirements; use `allkeys-lru` eviction policy.
- Warm caches on deploy to avoid thundering herd.

## LLM Provider Routing

- Use the intelligence router to select the cheapest model that meets quality requirements.
- Implement streaming responses to reduce time-to-first-token.
- Batch embedding requests where the provider supports it.
- Set budget caps per request/user to prevent cost overruns.

## Observability

- instrument key paths with Prometheus histograms (request latency, LLM token usage, DB query time).
- Trace high-latency requests in Jaeger; sample at 100% for errors, lower for healthy traffic.
- Set up Grafana alerts for p99 latency, error rate, and queue depth.

## Horizontal Scaling

- Scale app replicas behind a load balancer; ensure sticky sessions are NOT required.
- Use Redis for shared session state if horizontal scaling breaks in-process sessions.
- Partition Neo4j reads to a read replica if graph queries become a bottleneck.

## Resource Limits

- Set CPU/memory limits in `docker-compose.yml` or Kubernetes to prevent noisy neighbors.
- Monitor container resource usage; adjust limits based on actual utilization.
