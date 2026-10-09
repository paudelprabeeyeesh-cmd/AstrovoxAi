<<<<<<< HEAD
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
=======
.PHONY: help build up down test lint clean logs shell-backend shell-frontend migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	docker compose build

up: ## Start all services in detached mode
	docker compose up -d

down: ## Stop all services
	docker compose down

up-monitoring: ## Start services with monitoring stack
	docker compose --profile monitoring up -d

test: ## Run all tests
	cd 02-Backend && pytest tests/ -v --tb=short
	npm run test -- --run

lint: ## Run linters
	cd 02-Backend && ruff check app tests/
	npm run lint

typecheck: ## Run TypeScript type checking
	npm run typecheck

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi all

logs: ## Tail logs from all services
	docker compose logs -f --tail=100

logs-backend: ## Tail backend logs
	docker compose logs -f --tail=100 backend

logs-frontend: ## Tail frontend logs
	docker compose logs -f --tail=100 frontend

shell-backend: ## Open shell in backend container
	docker compose exec backend sh

shell-frontend: ## Open shell in frontend container
	docker compose exec frontend sh

migrate: ## Run database migrations
	cd 02-Backend && alembic upgrade head

migrate-down: ## Rollback last migration
	cd 02-Backend && alembic downgrade -1

backup-db: ## Backup PostgreSQL database
	@echo "Backing up database..."
	@mkdir -p backups
	@docker compose exec -T postgres pg_dump -U astrovox astrovox | gzip > backups/astrovox_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "Backup complete: backups/astrovox_$$(date +%Y%m%d_%H%M%S).sql.gz"

restore-db: ## Restore PostgreSQL database from backup
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore-db FILE=backups/astrovox_20240101_120000.sql.gz"; exit 1; fi
	gunzip < $(FILE) | docker compose exec -T postgres psql -U astrovox astrovox

health: ## Check health of all services
	@echo "Checking backend health..."
	@curl -s http://localhost:8000/health | jq .
	@echo "Checking frontend health..."
	@curl -s http://localhost: | head -1

deploy-staging: ## Deploy to staging
	@echo "Deploying to staging..."
	@kubectl apply -f k8s/
	@kubectl rollout status deployment/astrovox-backend -n astrovox --timeout=5m

deploy-prod: ## Deploy to production
	@echo "Deploying to production..."
	@kubectl apply -f k8s/
	@kubectl rollout status deployment/astrovox-backend -n astrovox --timeout=10m

test-backend: ## Run backend tests only
	python scripts/test_automation.py --backend

test-frontend: ## Run frontend tests only
	python scripts/test_automation.py --frontend

test-all: ## Run all automated checks
	python scripts/test_automation.py --all

coverage: ## Generate coverage reports
	cd 02-Backend && pytest --cov=app --cov-report=html --cov-report=term

mutation: ## Run mutation testing
	python scripts/run_mutation_tests.py
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
