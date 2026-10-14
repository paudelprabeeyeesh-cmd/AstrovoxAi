# Baseline

This is the **true measured** state of the backend test suite, produced by running it, not by
reading prior reports. Every prior `docs/BASELINE.md` treated its numbers as hypotheses; this one
is the actual output of the command below.

## How this was produced

```
cd 02-Backend
python -m pytest tests -q --no-header --timeout=90 --timeout-method=thread -p no:cacheprovider
```

| Field | Value |
|---|---|
| Date | 2026-10-14 |
| Commit | `0b703489` |
| Python | 3.14.5 |
| Command | `python -m pytest tests -q --no-header --timeout=90 --timeout-method=thread -p no:cacheprovider` |
| Duration | 649.66s (0:10:49) |
| Result | **393 failed, 6333 passed, 2 skipped, 29 errors** |

Raw output: `02-Backend/build_output_full.txt` (kept, not re-typeset).
Per-directory breakdown: `python scripts/baseline_breakdown.py`.

## What changed against the previous baseline

The previous document claimed: `tests/security` 93 passed, `tests/integration` 47 passed / 15 failed /
12 errors, and that "a full run did not complete".

| Claim | Measured now |
|---|---|
| "tests/security 93 passed" | **157 passed, 0 failed** |
| "tests/integration 47 passed, 15 failed, 12 errors" | **81 passed, 0 failed** |
| "a full run did not complete" | **Completes in 10m49s, 6740 tests collected** |

The security suite had more than doubled, and the integration suite more than doubled, because of
the suite-collection defect below.

## Root causes fixed before this baseline

The suite could not previously be trusted as a gate. These are the defects that made it so:

**Collection**
1. `tests/security`, `tests/services` and `tests/storage` were listed in `pytest.ini`'s
   `norecursedirs`, so `python -m pytest tests` never ran them at all. The security suite was
   invisible to the default run. **A check that is not collected cannot be a gate.**
2. `tests/conftest.py` synthesised a placeholder module for `app` when the target was not yet
   imported. A synthetic module has no `__path__`, so `from app import <name>` failed with
   "'app' is not a package" and 13 modules could not be collected.
3. A test overwrote `sys.modules["app"]` at *collection* time, which broke every module collected
   after it.
4. A test inserted `tests/` onto `sys.path`, shadowing the real `storage`, `services` and
   `analytics` packages with same-named test directories.
5. `storage/`, `services/` and `advanced_security/` were namespace packages, so they lost to the
   regular-package test directories with the same names.

**Termination** (the suite hung rather than failing)
6. `ResourcePool.acquire()` called `self._cond.wait(timeout)` where `timeout` was `None`, which
   blocks forever; `wait(None)` also never signals a timeout, so `acquire()` deadlocked on its own
   non-reentrant lock.
7. `sandboxing/approval_store.py::cleanup_expired` held the store's non-reentrant lock while calling
   `_archive`, which re-acquired it.
8. `tests/test_automation.py::test_pytest_can_collect_tests` ran `pytest --collect-only` over the
   whole suite from inside the suite: self-recursive and never returned.
9. `tests/resource_management/test_resource_pool.py` called `acquire()` on an empty pool with no
   timeout, blocking forever.

**Correctness surfaced by making the suite runnable**
10. `database/database.py` (1220 lines) was **three concatenated modules**. `init_db`, `get_db` and
    `create_user` were each defined twice or three times and only the last definition was reachable;
    `_ensure_tables_rag` was defined but never called, so the retrieval tables were never created.
11. The two database modules read **different environment variable spellings** (`ASTROVOX_DB_PATH`
    vs `Astravox_DB_PATH`). With both set, the schema was created in one file and the queries ran
    against another.
12. `app/auth_utils.py` was **two concatenated modules** with an undefined `logger` and two
    conflicting `get_user_id_from_token` definitions.
13. `app/supabase_client.py` and its repository-layer duplicate placed a `return _Fallback...()`
    *after* the `raise`, so the documented fallback was unreachable and importing the app required
    live Supabase credentials.
14. Five `time.sleep` calls inside `async def` provider methods blocked the event loop for **every**
    concurrent request, not just the failing caller. This was a measured defect found by
    `tests/performance/test_performance_regression.py::TestAsyncIOCompliance`.
15. Backup filenames had one-second resolution, so backups taken in the same second overwrote each
    other silently.
16. `sandboxing/tool_sandbox.py` called `CircuitBreaker.call(...)`, which does not exist, so every
    sandboxed tool failed with `AttributeError` and no circuit breaker ever opened.

## Current failure profile

All 6740 collected tests now run to completion in ~11 minutes. The remaining failures are **not**
uniformly distributed and are mostly outside the security surface:

| Directory | Failed | Error |
|---|---|---|
| `tests/performance` | 18 | 0 |
| `tests/multimodal` | 16 | 0 |
| `tests/route_tests` | 13 | 0 |
| `tests/monitoring` | 11 | 0 |
| `tests/representation_learning` | 10 | 0 |
| `tests/fault_tolerance` | 9 | 0 |
| `tests/cryptographic_protocols` | 8 | 0 |
| `tests/advanced_planning` … `tests/alignment` | 7 | 0 |
| other experimental/domain modules | ~291 | 29 |
| `tests/database` (Word morpholgy) | 20 | 0 |
| `tests/storage` | 1 | 0 |
| **`tests/security`** | **0** | **0** |

The three suites that gate security and core API contracts (`tests/security`, `tests/integration`,
`tests/database`) are green.

## Known failure causes (not yet fixed)

These are diagnosed, not guessed at:
- `tests/performance/test_performance_regression.py`: patches `app.chat.get_user_id_from_token`,
  which does not exist on the module (the tests were written against an older API); hard-coded
  latency baselines (e.g. "RAG retrieval 0.59s exceeds 150ms baseline"); and
  `from app.vector.index import VectorIndex`, a symbol that is not in the module.
- `tests/multimodal` and the domain modules: API drift between the experimental packages and their
  tests, which is what `docs/MODULE_INVENTORY.md` describes.

## Reproduce

```
cd 02-Backend
python -m pytest tests -q --no-header --timeout=90 --timeout-method=thread -p no:cacheprovider
python scripts/baseline_breakdown.py
```

`make test-backend` is **not** used for this run: it sets `COVERAGE_CORE=true`, which lowers the
thresholds, and this measurement is meant to be unadjusted.
