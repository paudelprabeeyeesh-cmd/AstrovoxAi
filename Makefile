.PHONY: help install test lint typecheck clean run dev build build-backend build-frontend docker-test security-scan sbom release release-dry clean-dev quality

help:
	@echo "AstrovoxAI — available targets:"
	@echo "  make install        — install dependencies"
	@echo "  make test           — run backend test suite"
	@echo "  make test-quick     — run core backend tests"
	@echo "  make lint           — run backend linting"
	@echo "  make typecheck      — run backend type checking"
	@echo "  make build          — build all Docker images"
	@echo "  make build-backend  — build backend Docker image"
	@echo "  make build-frontend — build frontend Docker image"
	@echo "  make docker-test    — run tests in Docker containers"
	@echo "  make security-scan  — run security scans (bandit, pip-audit, npm audit)"
	@echo "  make sbom           — generate SBOM for supply chain"
	@echo "  make release        — create a new release"
	@echo "  make release-dry    — simulate a release without pushing"
	@echo "  make quality        — run code quality dashboard"
	@echo "  make clean          — remove caches and temp files"
	@echo "  make clean-dev      — remove dev artifacts"
	@echo "  make run            — start development server"
	@echo "  make dev            — install deps and start dev server"

install:
	cd 02-Backend && pip install -r requirements.txt

test:
	cd 02-Backend && pytest

test-quick:
	cd 02-Backend && pytest tests/test_executor_compiler.py tests/test_executor_runtime.py tests/test_kernel.py tests/test_integration_stage44.py tests/test_security_hardening.py tests/test_performance.py tests/test_infrastructure.py tests/test_workflow_engine.py

lint:
	cd 02-Backend && ruff check app tests
	cd 02-Backend && flake8 app tests --max-line-length 120 --statistics --extend-ignore=E203,W503 || true

typecheck:
	cd 02-Backend && mypy app --ignore-missing-imports --follow-imports=silent || true

build: build-backend build-frontend

build-backend:
	docker build -f Dockerfile.backend -t astrovoxai/backend:latest .

build-frontend:
	docker build -f Dockerfile.frontend -t astrovoxai/frontend:latest .

docker-test:
	docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build backend redis postgres
	sleep 15
	docker exec astrovox-backend python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing || true
	docker compose -f docker-compose.yml -f docker-compose.override.yml down -v

security-scan:
	cd 02-Backend && pip install bandit pip-audit safety
	bandit -r app/ -f json -o bandit-report.json -ll || true
	pip-audit -r requirements.txt --format json > pip-audit-report.json || true
	safety check --file=requirements.txt --full-report || true
	cd .. && npm audit --audit-level=high || true

sbom:
	mkdir -p sboms
	docker build -f Dockerfile.backend -t astrovoxai/backend:sbom .
	syft astrovoxai/backend:sbom -o spdx-json=sboms/backend-sbom.spdx.json || true
	syft astrovoxai/backend:sbom -o cyclonedx-json=sboms/backend-sbom.cyclonedx.json || true
	docker build -f Dockerfile.frontend -t astrovoxai/frontend:sbom .
	syft astrovoxai/frontend:sbom -o spdx-json=sboms/frontend-sbom.spdx.json || true
	syft astrovoxai/frontend:sbom -o cyclonedx-json=sboms/frontend-sbom.cyclonedx.json || true
	@echo "SBOMs saved to sboms/"

release:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=x.y.z"; exit 1; fi
	bash scripts/release.sh $(VERSION)

release-dry:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release-dry VERSION=x.y.z"; exit 1; fi
	bash scripts/release.sh --dry-run $(VERSION) || true

quality:
	mkdir -p code-quality-reports
	python tools/code-quality/dashboard.py || true
	@echo "Quality reports saved to code-quality-reports/"

clean:
	find 02-Backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find 02-Backend -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf 02-Backend/.pytest_cache 2>/dev/null || true
	rm -rf 02-Backend/.mypy_cache 2>/dev/null || true
	rm -rf 02-Backend/.ruff_cache 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	rm -rf .mypy_cache 2>/dev/null || true
	rm -rf .ruff_cache 2>/dev/null || true
	rm -rf node_modules/.cache 2>/dev/null || true
	rm -rf code-quality-reports 2>/dev/null || true
	rm -rf sboms 2>/dev/null || true
	rm -f bandit-report.json pip-audit-report.json 2>/dev/null || true

clean-dev:
	docker compose -f docker-compose.yml -f docker-compose.override.yml down -v --remove-orphans || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .venv -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -prune -exec rm -rf {} + 2>/dev/null || true

run:
	cd 02-Backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev: install run
