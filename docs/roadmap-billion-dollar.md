# AstrovoxAI — Long-Term Roadmap to a $1B+ Valuation

> Brutally honest, actionable, solo-developer-to-company guidance.
> Assumes limited capital, high ambition, and willingness to make hard choices.

---

## 1. Technical Architecture & Cost Engineering

### 1.1 Model Routing

**Principle:** Never send a $200 task to a $200 model. Route by task complexity, latency tolerance, and cost.

**Implementation:**
- **Router service** (`app/model_router.py`) with three tiers:
  - **Tier 1 — Cheap & fast:** open-source or low-cost API models for classification, extraction, formatting, simple summarization
  - **Tier 2 — Balanced:** mid-tier API models for reasoning, multi-step planning, code generation
  - **Tier 3 — Expensive & capable:** frontier models for high-stakes generation, research synthesis, complex tool use
- **Cost-aware routing rules:**
  - If input < 500 tokens and expected output < 300 tokens → Tier 1
  - If tool calls required > 2 → Tier 2 minimum
  - If user explicitly requests “best model” or payload contains PII-sensitive reasoning → Tier 3
- **Fallback ladder:** Tier 3 fails → retry on Tier 2 → retry on Tier 1 with degraded prompt → surface fallback UI to user
- **Tooling:** LiteLLM proxy, OpenRouter aggregator, or custom router with per-model cost lookup table refreshed daily from provider pricing pages
- **Metrics to track:** cost per 1k tokens by model, p50/p95 TTFT by model, success rate by model, fallback frequency

**Numbers:**
- Target: 70% of requests on Tier 1, 25% on Tier 2, 5% on Tier 3
- Cost reduction target: 60–80% vs. routing everything to GPT-6 class models
- Latency budget: Tier 1 < 300ms TTFT, Tier 2 < 800ms, Tier 3 < 2s

---

### 1.2 RAG Pipeline

**Principle:** Retrieval quality > retrieval quantity. Every irrelevant chunk is a token tax and a hallucination risk.

**Implementation:**
- **Hybrid search stack:**
  - Dense vector search via `pgvector` or Qdrant
  - Sparse BM25 via `tantivy` or PostgreSQL full-text search
  - Reranker: Cohere Rerank 3, BGE-Reranker-v2-m3, or a small cross-encoder deployed as a Triton endpoint
- **Chunking strategy:**
  - Base: 512 tokens with 10% overlap for general text
  - Code: 256 tokens, 0% overlap, AST-aware splitting
  - Tables/JSON: preserve structure, chunk by row or object
  - Long-form: recursive character splitting with heading-aware boundaries
- **Metadata enrichment per chunk:**
  - Source document hash, page/section, creation timestamp, access count, last-retrieval timestamp, trust score
- **Incremental indexing:**
  - Webhook or queue-based ingestion; never re-index the whole corpus on every update
  - Tombstone records for deletions; background compaction every 24h
- **Caching:**
  - Semantic cache keyed on query embedding + top-3 retrieved chunk IDs
  - TTL: 1 hour for general queries, 5 minutes for time-sensitive data
- **Tooling:** LlamaIndex or Haystack as orchestration layer; `sentence-transformers` for embeddings; `flag-embedding` for reranking

**Metrics:**
- Retrieval precision@5 > 85%
- Reranker lift: precision@5 improves by ≥ 15% vs. dense-only
- Cache hit rate > 30% for repeat queries
- End-to-end RAG latency p95 < 1.2s

---

### 1.3 LLMOps

**Principle:** If you can’t measure it, you can’t improve it. Treat prompts and retrieval pipelines as versioned code.

**Implementation:**
- **Prompt registry:**
  - Every prompt template stored in version control with schema, description, owner, creation date, and performance baseline
  - Use `prompt-metadata` JSON sidecar files or a dedicated `prompts/` directory with tests
- **Evaluation pipeline:**
  - Golden test set: 500–2000 human-verified Q&A pairs per major use case
  - Automated nightly evals: exact match, semantic similarity (BERTScore, BLEURT), LLM-as-judge (GPT-5.6 class model grading outputs)
  - Regression gate: no prompt change may drop eval score > 2% without manual review
- **A/B testing:**
  - Dual-write 10% traffic to prompt variants; compare win rate, token cost, user satisfaction
  - Use sequential testing to avoid peeking; minimum sample 1,000 conversations per variant
- **Observability integration:**
  - Every LLM call logged with: prompt version, model, temperature, top-p, stop sequences, token usage, latency, retrieval context, user feedback score
- **Tooling:** PromptFlow, Helicone or LangSmith for tracing; Weights & Biases or MLflow for eval tracking; `deepeval` for unit-test-style LLM evals

**Metrics:**
- Eval cadence: nightly at minimum, real-time for high-stakes prompts
- Golden test set coverage: 100% of production prompts
- Time to detect prompt regression: < 24 hours
- False-positive rate for safety evals: < 0.1%

---

### 1.4 Cost Engineering

**Principle:** Token cost is a first-class product signal. Optimize before you scale.

**Implementation:**
- **Token budget by user tier:**
  - Free tier: 100k tokens/month hard cap
  - Pro tier: 2M tokens/month soft cap with overage billing at cost + 30%
  - Enterprise: negotiated quota with burst pricing
- **Semantic caching:**
  - Cache exact and near-exact query results at the embedding level
  - Expected hit rate: 25–40% for support/FAQ use cases, 10–20% for creative tasks
- **Context trimming:**
  - Sliding window with importance scoring: keep system prompt, last 4 messages, and top-3 retrieved chunks; summarize older context if > 80% of context window
  - Tool: `llmlingua-2` or custom summarizer for conversation history compression
- **Batch inference:**
  - For offline jobs (embeddings, eval, bulk classification), batch 32–128 requests per API call
  - Savings: 30–50% on provider batch pricing tiers
- **Dynamic batching for reranker:**
  - Accumulate rerank requests over 50ms windows; process in batches of 16–32
- **Cost attribution:**
  - Per-user, per-team, per-feature cost tracking in `app/cost_management.py`
  - Alert when daily cost exceeds 120% of 7-day average
- **Tooling:** Token counting via `tiktoken`; cost dashboards in Grafana; budget alerts via PagerDuty

**Numbers:**
- Target: $0.02–$0.05 per successful task completion (including retries, retrieval, reranking)
- Semantic cache ROI: 1 cache hit saves ~$0.005–$0.02 depending on model tier
- Break-even self-hosting: > 500M tokens/month at current API pricing; revisit quarterly

---

### 1.5 Compute & Hosting

**Implementation:**
- **API-first for inference:** No self-hosting of frontier models until > 500M tokens/month and > 80% on Tier 1/2
- **Self-hosted stack (when justified):**
  - `vLLM` or `TGI` for open-weight models (Llama 4, Mistral Large, Qwen 3)
  - Kubernetes with spot instances + CPU fallback for batch workloads
  - Model weights on S3/Cloudflare R2; cache on node-local NVMe
- **Serverless for control-plane:**
  - FastAPI on Fly.io, Railway, or AWS Fargate for API, webhooks, scheduler
  - PostgreSQL on Supabase or RDS; Redis on Upstash or ElastiCache
- **Cold-start optimization:**
  - Lazy-load model clients; connection pooling; keep-alive for provider HTTP connections
- **Tooling:** `kubectl` + Helm for infrastructure; Terraform for IaC; Pulumi for serverless stacks

**Break-even math:**
- API cost: ~$2–$5 per 1M output tokens (frontier models)
- Self-hosted cost: ~$0.50–$1.50 per 1M output tokens (amortized GPU + power + ops)
- Self-hosting justified when: (monthly output tokens × API cost per 1M) > (GPU monthly cost + ops overhead)
- Example: 1B output tokens/month = $2,000–$5,000 API cost vs. $1,500–$3,000 self-hosted → marginal benefit, higher risk
- Wait until 2–5B output tokens/month before serious self-hosting evaluation

---

### 1.6 Observability

**Implementation:**
- **Metrics to emit per request:**
  - `llm.tokens.prompt`, `llm.tokens.completion`, `llm.cost.total`, `llm.latency.ttft_ms`, `llm.latency.total_ms`
  - `rag.retrieval.latency_ms`, `rag.retrieval.precision`, `rag.reranker.latency_ms`, `rag.cache.hit`
  - `router.decision`, `router.fallback.count`, `workflow.step.duration_ms`
- **Dashboards:**
  - Executive: daily cost, active users, NPS, revenue, burn multiple
  - Engineering: p95 latency, error rate, cache hit rate, fallback frequency
  - Product: feature adoption, workflow completion rate, user satisfaction by feature
- **Alerting:**
  - Cost spike > 2x daily average in 1 hour → page on-call
  - p95 latency > 3s for > 5 minutes → page
  - Cache hit rate drops > 20% WoW → Slack alert
- **Tooling:** Prometheus + Grafana; OpenTelemetry for distributed tracing; Sentry for errors; Datadog or Honeycomb for APM

**Targets:**
- Dashboard refresh: 30 seconds
- Alert MTTR: < 15 minutes for P1, < 4 hours for P2
- Data retention: 90 days for metrics, 1 year for aggregated billing

---

### 1.7 Security & Guardrails

**Implementation:**
- **Input guardrails:**
  - PII detection and redaction before sending to LLM (use Microsoft Presidio or similar)
  - Prompt injection classifier: fine-tuned BERT or LLM-based detector on known jailbreak patterns
  - Max output length enforcement; regex allowlisting for tool call arguments
- **Output guardrails:**
  - Content safety classifier for user-facing outputs (use provider moderation + custom classifier)
  - Citation requirement: every factual claim must cite a retrieved chunk or tool result
  - Hallucination detection: compare claims against retrieval context; flag uncited assertions
- **Agent guardrails:**
  - Human-in-the-loop for high-risk actions: sending emails, financial transactions, code execution on production systems
  - Rate limiting per agent per user; circuit breakers on repeated failures
  - Audit log: immutable append-only log of all agent actions with timestamp, actor, action, result, rationale
- **Data isolation:**
  - Per-tenant embedding namespaces or separate indices
  - Encryption at rest (AES-256) and in transit (TLS 1.3)
- **Tooling:** Presidio for PII; Guardrails AI or NeMo Guardrails for LLM safety; OpenTelemetry for audit trails

**Standards:**
- SOC 2 Type II by month 18
- GDPR/CCPA compliance by month 12
- Annual penetration test by certified firm
- Bug bounty program after Series A
