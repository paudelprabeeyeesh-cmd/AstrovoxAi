# Testing Plan

## Scope

This plan covers backend validation for AstravoxAi Engine v1.0.0.

## Test Suites

| Suite | Focus | Command |
|-------|-------|---------|
| Compiler | DSL parsing, optimization, caching | `pytest tests/test_executor_compiler.py` |
| Runtime | Execution, retries, checkpoints | `pytest tests/test_executor_runtime.py` |
| Kernel | Event bus, scheduler, model router | `pytest tests/test_kernel.py` |
| Integration | E2E pipeline, production config | `pytest tests/test_integration_stage44.py` |
| Security | JWT, RBAC, input validation | `pytest tests/test_security_hardening.py` |
| Performance | Cache, metrics, decorators | `pytest tests/test_performance.py` |
| Infrastructure | Job queue, event bus, circuit breaker | `pytest tests/test_infrastructure.py` |
| Workflow | Workflow engine, templates, cloning | `pytest tests/test_workflow_engine.py` |

## Current Status

- 141 core tests passing
- Some integration/E2E tests have pre-existing rate-limiting test isolation issues

## Stress Testing

- Run compiler with 10,000-step programs
- Run runtime with 100 parallel tasks
- Monitor memory usage with `tracemalloc` or `memray`

## Failure Injection

- Toggle network failures in provider adapters
- Inject latency with `asyncio.sleep`
- Verify circuit breaker opens and recovers

## Backup / Restore

- Verify `BackupManager` creates and restores snapshots
- Verify `StabilityMonitor` summarizes health correctly

## Acceptance Criteria

- All core test suites pass
- No memory leaks in 1-hour continuous run
- Compiler cache remains stable under concurrent access
- Runtime retries recover from transient failures
