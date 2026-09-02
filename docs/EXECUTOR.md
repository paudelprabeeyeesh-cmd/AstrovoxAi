# Custom AI Execution Engine (Stage 34)

The AI Execution Engine is the architectural core of AstrovoxAI. It
replaces ad-hoc request handling with a compiled, optimized, and
runtime-managed execution pipeline.

## Architecture

```
DSL Source
   ↓ Lexer
Tokens
   ↓ Parser
AST
   ↓ Compiler
Execution Graph (with optimization)
   ↓ Runtime
Results (with checkpoints, retries, parallelism)
   ↓ Memory Brain / Reasoning / Learning
Improvement
```

## Components

| Module | Responsibility |
|--------|----------------|
| `executor/dsl.py` | Lexer, parser, AST for the AI workflow language |
| `executor/compiler.py` | AST → execution graph, cost estimation, fusion, dead-step elimination |
| `executor/runtime.py` | Parallel execution, retries, timeouts, checkpoints |
| `executor/cluster.py` | Distributed worker registry, heartbeats, failover |
| `executor/memory_brain.py` | Working, long-term, episodic, semantic, procedural memory |
| `executor/reasoning.py` | Chain, tree, graph, debate, reflection, verification |
| `executor/learning.py` | Feedback, failure tracking, improvement reports |
| `executor/performance.py` | Profiler, cache, batcher, load tester |
| `executor/reliability.py` | Chaos testing, fault injection, recovery, backup |
| `executor/api.py` | FastAPI surface (14 routes under `/executor`) |

## DSL

Example:

```
LOAD "doc.pdf" AS doc
SEARCH "auth" IN doc LIMIT 10 AS hits
SUMMARIZE hits LENGTH 200 AS summary
ASK "write a report from summary" AS report
EMAIL "report.md" TO "alice@example.com"
```

Statements produce values bound to names; later statements may reference
earlier bindings. Parallel blocks are supported:

```
PARALLEL {
  LOAD "a" AS a
  LOAD "b" AS b
}
ASK "combine a b" AS combined
```

## Compilation

The compiler performs:

- **Lowering** — AST statements become typed steps.
- **Cost estimation** — each step kind has an empirical cost weight.
- **Parallel group detection** — independent steps are grouped into waves.
- **Dead-step elimination** — unused steps (except first/last) are removed.
- **Execution fusion** — adjacent `SEARCH` + `SUMMARIZE` collapse into one step.
- **Constant propagation** — LOAD sources are inlined for downstream steps.
- **Plan caching** — identical ASTs reuse the same plan.

## Runtime

- `Runtime.execute(graph)` runs an `ExecutionGraph` with:
  - A configurable max parallelism (semaphore).
  - Per-step retries up to `max_retries`.
  - Per-step timeouts.
  - Cancellation support.
  - Checkpoints that capture every step's state for resumability.

## Memory Brain

- **Working memory** — small, fast, per-session; LRU eviction.
- **Long-term memory** — persistent; consolidation boosts importance.
- **Episodic memory** — time-ordered events; session filter.
- **Semantic memory** — facts with confidence; gradual decay.
- **Procedural memory** — patterns (how-to steps).

## Reasoning Strategies

- **Chain** — linear step-by-step deduction.
- **Tree** — branching paths with pruning.
- **Graph** — link related facts and traverse.
- **Debate** — generate pro/con and judge.
- **Reflection** — iterate on prior answers.
- **Verification** — score candidate answers against the problem.

## API Surface (14 routes under `/executor`)

- `POST /executor/compile` — DSL source → graph.
- `POST /executor/execute` — DSL source → executed result.
- `POST /executor/memory/remember` — store memory.
- `POST /executor/memory/recall` — search memory.
- `GET  /executor/memory/stats` — brain statistics.
- `POST /executor/reason` — reasoning over a problem.
- `POST /executor/learning/feedback` — record feedback.
- `GET  /executor/learning/report` — improvement report.
- `GET  /executor/learning/summary` — metrics summary.
- `GET  /executor/performance/profiler` — profiler stats.
- `GET  /executor/performance/cache` — cache stats.
- `POST /executor/chaos/experiment` — run a chaos experiment.
- `GET  /executor/chaos/results` — chaos history.
- `GET  /executor/cluster/workers` — worker registry.

## Testing

91 unit tests cover DSL parsing, compilation, runtime execution,
distributed cluster, memory brain, reasoning strategies, learning
engine, performance lab, and reliability module. Run with:

```
pytest tests/test_executor_*.py
```