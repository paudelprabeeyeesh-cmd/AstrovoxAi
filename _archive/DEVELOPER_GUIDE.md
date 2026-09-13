# Developer Guide

This guide explains how to work on the AstrovoxAi backend and frontend. It covers setup, debugging, testing, and common workflows.

## Backend Development

### Running the API

```bash
cd 02-Backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
cd 02-Backend
pytest
```

Run a specific test file:
```bash
pytest tests/test_executor_compiler.py
```

Run a specific test:
```bash
pytest tests/test_executor_compiler.py::CompilerTest::test_fusion
```

### Backend Modules

- `app/main.py` — FastAPI app and route registration
- `app/executor/dsl.py` — DSL lexer and parser
- `app/executor/compiler.py` — DSL compiler and optimizations
- `app/executor/runtime.py` — Execution runtime
- `app/kernel/` — Core kernel (scheduler, event bus, model router)
- `app/providers/` — AI provider implementations
- `app/enterprise/` — Organization and RBAC
- `app/workspace.py` — Workspace features

### Debugging

Use `print` or the configured logger:
```python
from app.logging_config import get_logger
logger = get_logger(__name__)
logger.info("message")
```

### Profiling

Use Python's built-in profilers:
```bash
python -m cProfile -o profile.stats script.py
snakeviz profile.stats
```

## Frontend Development

### Running the Dev Server

```bash
npm run dev
```

### Building

```bash
npm run build
```

### Linting

```bash
npm run lint
```

## Common Tasks

### Adding a New AI Provider

1. Create a new class in `app/providers/` inheriting from `BaseProvider`.
2. Register it in `app/providers/factory.py`.
3. Add tests in `02-Backend/tests/`.

### Adding a New API Endpoint

1. Add the route in the appropriate module under `app/`.
2. Register it in `app/main.py`.
3. Add request/response models with Pydantic.
4. Add tests.

### Modifying the DSL

1. Update the AST nodes in `app/executor/dsl.py`.
2. Update the compiler in `app/executor/compiler.py`.
3. Update the runtime handler in `app/executor/runtime.py`.
4. Add tests in `tests/test_executor_compiler.py` and `tests/test_executor_runtime.py`.

## Troubleshooting

- Import errors: ensure you are running from `02-Backend/` and the virtual environment is active.
- Rate limit errors in tests: tests share in-memory state; run failing tests in isolation to diagnose.
- Frontend build errors: delete `node_modules` and run `npm install` again.
