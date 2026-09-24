# Testing Guide

## Running Tests
```bash
pytest
```
Config in `pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`).

## Structure
- `tests/test_*.py` — Unit/integration tests by feature (auth, chat, memory, providers, security, rag, etc.).
- `tests/conftest.py` — Shared fixtures.
- `tests/run_benchmarks.py`, `tests/benchmark.py` — Performance benchmarks.

## Conventions
- Use `pytest` + `pytest-asyncio`; mark async tests accordingly.
- Prefer integration tests against real services when possible (see `docker-compose.yml` services).
- Keep tests in `tests/`, mirroring `app/` module names where practical.
- Run `pytest tests/` before pushing.
