# AstrovoxAI Backend — Maintenance & Optimization Roadmap

## Phase 1: Stabilize

Focus: bug resolution, technical debt reduction, and maintaining test suite integrity.

### Task 1.1 — Bug Triage & Incident Capture
- Instrument `app.exceptions.AstrovoxError` subclasses with structured context fields (`provider`, `model_id`, `tenant_id`, `request_id`).
- Add an `unhandled_exception` handler in the ASGI middleware stack that captures the traceback and enqueues it for review.
- **Commit boundary**: each new exception subclass + its ASGI wiring is one commit.

### Task 1.2 — Test-Suite Enforcement
- Configure `pytest.ini` / `pyproject.toml` with `--strict-markers`, `--tb=short`, and a CI threshold (fail build if coverage drops below current baseline).
- Add a `tests/conftest.py` fixture that automatically mocks external provider HTTP calls to keep tests deterministic.
- **Commit boundary**: one commit per configuration change plus the shared fixture.

### Task 1.3 — Static Analysis Hygiene
- Run `ruff check .` and `mypy app/` in CI; fix all reported issues before new feature work proceeds.
- Treat every lint or typing error as a standalone commit to keep diffs reviewable.
- **Commit boundary**: each lint fix batch is a commit.

### Task 1.4 — Completed Refactor: Centralize Shared Utilities
- `CircuitState` enum deduplicated into `app/utils.py`.
- `now()` helper replaces direct `time.time()` calls in core modules (`executor`, `jobs`, `agent`, `knowledge_base`, `ai_kernel`, `multi_agent`, `workflow_engine`).
- **Commit boundary**: one commit per module refactored.

## Phase 2: Simplify

Focus: directory restructuring, file reduction, modularizing oversized files, and eliminating code duplication.

### Task 2.1 — Audit File Count & Module Responsibilities
- Run a tree-based audit to identify files > 600 LOC or with > 3 distinct responsibilities (e.g., `caching.py`, `circuit_breaker.py`).
- Produce a `docs/refactor-candidates.md` mapping each oversized file to a proposed split.
- **Commit boundary**: document commit first; each split is a subsequent commit.

### Task 2.2 — Directory Restructuring
- Consolidate `app/providers/` subpackages that expose only 1–2 classes into a single `providers/core.py` module.
- Move rarely used utilities (`app/utils.py` extensions, analytics helpers) into a `libs/` package.
- **Commit boundary**: move + rename each package as an atomic commit.

### Task 2.3 — Eliminate Enum Duplication
- Compare `AgentState` in `app/agent.py` vs `app/multi_agent.py`. If they diverge intentionally, document the difference in `docs/enums.md`; if they overlap, merge into `app/utils.py`.
- **Commit boundary**: one commit per enum deduplication.

### Task 2.4 — Remove Dead Imports & Unused Dependencies
- Use `ruff` to flag unused imports; delete them module-by-module.
- Audit `requirements.txt` for packages with no import references in `app/`.
- **Commit boundary**: one commit per module or dependency batch.

## Phase 3: Optimize

Focus: performance profiling, memory footprint reduction, startup time improvement, and addressing specific measured bottlenecks.

### Task 3.1 — Baseline Profiling
- Run `python -m cProfile -o profile.out` on representative endpoints (chat, upload, workflow trigger).
- Use `snakeviz profile.out` or `py-spy record` to identify top-10 hot functions.
- Document the baseline in `docs/performance-baseline.md`.
- **Commit boundary**: profiling scripts + baseline report commit.

### Task 3.2 — Startup Time Reduction
- Lazy-load heavy singletons (`knowledge_base`, `executor`, `workflow_engine`) behind function calls instead of module-import side effects.
- Measure cold-start time before/after with `time.perf_counter()`.
- **Commit boundary**: one commit per lazy-load refactor.

### Task 3.3 — Memory Footprint Optimization
- Replace in-memory dictionaries holding large payloads (e.g., `caching.py`, `analytics.py`) with bounded LRU caches (`functools.lru_cache` or `cachetools.LRUCache`).
- Add `__slots__` to hot dataclasses (`Job`, `Task`, `WorkflowExecution`) after confirming memory savings with `tracemalloc`.
- **Commit boundary**: one commit per memory optimization.

### Task 3.4 — Async I/O Audit
- Scan for synchronous `requests` / `time.sleep` calls in `async` functions.
- Replace with `httpx.AsyncClient` + `asyncio.sleep`.
- **Commit boundary**: one commit per module converted.


