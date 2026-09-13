.PHONY: help test lint typecheck clean run dev install

help:
	@echo "AstravoxAi Backend — available targets:"
	@echo "  make install    — install dependencies"
	@echo "  make test       — run test suite"
	@echo "  make test-quick — run core test suites only"
	@echo "  make lint       — run linting"
	@echo "  make typecheck  — run type checking"
	@echo "  make clean      — remove caches and temp files"
	@echo "  make run        — start development server"

install:
	pip install -r requirements.txt

test:
	cd 02-Backend && pytest

test-quick:
	cd 02-Backend && pytest tests/test_executor_compiler.py tests/test_executor_runtime.py tests/test_kernel.py tests/test_integration_stage44.py tests/test_security_hardening.py tests/test_performance.py tests/test_infrastructure.py tests/test_workflow_engine.py

lint:
	cd 02-Backend && flake8 app tests

typecheck:
	cd 02-Backend && mypy app

clean:
	find 02-Backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find 02-Backend -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf 02-Backend/.pytest_cache 2>/dev/null || true
	rm -rf 02-Backend/.mypy_cache 2>/dev/null || true

run:
	cd 02-Backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev: install run
