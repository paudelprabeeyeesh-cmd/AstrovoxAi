# Testing Guide

## Running Tests

```bash
pytest
```

Config lives in `pyproject.toml`:
- `testpaths = ["tests"]`
- `asyncio_mode = "auto"`
- `pythonpath = ["."]`

## Directory Structure

| Path | Purpose |
|-----|---------|
| `tests/test_*.py` | Unit and integration tests by feature (auth, chat, memory, providers, security, rag, etc.) |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/run_benchmarks.py`, `tests/benchmark.py` | Performance benchmarks |

## Conventions

- Use `pytest` + `pytest-asyncio`; mark async tests with `@pytest.mark.asyncio`.
- Prefer integration tests against real services when possible (see `docker-compose.yml` services).
- Keep tests in `tests/`, mirroring `app/` module names where practical.
- Use descriptive test names: `test_<behavior>_<condition>_<expected_result>`.
- Run `pytest tests/` before pushing; CI runs the full suite.

## Fixtures

- Define shared fixtures in `tests/conftest.py`.
- Use `db_session` for database-backed tests.
- Use `client` for FastAPI TestClient or AsyncClient tests.

## Coverage

- Aim for meaningful coverage, not just high percentages.
- Focus on critical paths: auth, LLM provider routing, memory operations, and security-sensitive code.
