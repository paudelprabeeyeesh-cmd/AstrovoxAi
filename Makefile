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
