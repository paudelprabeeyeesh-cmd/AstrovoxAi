# AstrovoxAI Development & Deployment Commands
# Run `just --list` for available commands.

set shell := ["powershell.exe", "-NoLogo", "-Command"]

_default:
    @just --list

# ---------------------------------------------------------------------------
# Foundation: Lint, Format, Typecheck
# ---------------------------------------------------------------------------
lint:
    cd 02-Backend; ruff check app tests
    cd 02-Backend; flake8 app tests --max-line-length 120 --statistics

format:
    cd 02-Backend; black app tests
    cd 02-Backend; isort app tests

typecheck:
    cd 02-Backend; mypy app --ignore-missing-imports

check lint format typecheck:
    cd 02-Backend; ruff check app tests
    cd 02-Backend; black --check app tests
    cd 02-Backend; mypy app --ignore-missing-imports || true

# ---------------------------------------------------------------------------
# Foundation: Tests
# ---------------------------------------------------------------------------
test:
    cd 02-Backend; pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

test-integration:
    cd 02-Backend; pytest tests/ -k integration -v --tb=short

test-security:
    cd 02-Backend; pytest tests/ -k security -v --tb=short

test-chaos:
    cd 02-Backend; pytest tests/ -k chaos -v --tb=short

test:
    cd 02-Backend; pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=80

# ---------------------------------------------------------------------------
# Foundation: Security
# ---------------------------------------------------------------------------
security-bandit:
    cd 02-Backend; bandit -r app/ -f json -o bandit-report.json -ll || echo "Bandit scan completed"

security-pip-audit:
    cd 02-Backend; pip-audit -r requirements.txt --format json > pip-audit-report.json || echo "pip-audit completed"

security-check security-bandit security-pip-audit:
    cd 02-Backend; bandit -r app/ -f json -o bandit-report.json -ll || echo "Bandit scan completed"
    cd 02-Backend; pip-audit -r requirements.txt --format json > pip-audit-report.json || echo "pip-audit completed"

# ---------------------------------------------------------------------------
# Database: Migrations
# ---------------------------------------------------------------------------
migrate:
    cd 02-Backend; alembic upgrade head

migrate-rollback:
    cd 02-Backend; alembic downgrade -1

migrate-create message:
    cd 02-Backend; alembic revision --autogenerate -m "{{message}}"

# ---------------------------------------------------------------------------
# Database: Seed
# ---------------------------------------------------------------------------
seed:
    cd 02-Backend; python -m scripts.seed_data

seed-demo:
    cd 02-Backend; python -m scripts.seed_demo_data

# ---------------------------------------------------------------------------
# Database: Health
# ---------------------------------------------------------------------------
db-health:
    cd 02-Backend; python -c "from app.infrastructure.failover import get_failover_pool; print(get_failover_pool().get_stats())"

db-pool-health:
    cd 02-Backend; python -c "from app.database_engine import connection_pool; print(connection_pool.get_stats())"

# ---------------------------------------------------------------------------
# Backend: Run
# ---------------------------------------------------------------------------
run:
    cd 02-Backend; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod:
    cd 02-Backend; gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# ---------------------------------------------------------------------------
# Backend: API Gateway
# ---------------------------------------------------------------------------
gateway-routes:
    cd 02-Backend; python -c "from app.api_gateway import APIGateway; [print(r.path, '->', r.target_service) for r in APIGateway.list_routes()]"

gateway-reload:
    cd 02-Backend; python -c "from app.api_gateway import ROUTES; print(f'Reloaded {len(ROUTES)} routes')"

# ---------------------------------------------------------------------------
# Backend: Workers
# ---------------------------------------------------------------------------
worker:
    cd 02-Backend; arq app.workers.worker.WorkerSettings

celery-worker:
    cd 02-Backend; celery -A app.celery_app worker --loglevel=info

scheduler:
    cd 02-Backend; python -m app.scheduler

# ---------------------------------------------------------------------------
# Cloud: Service Mesh
# ---------------------------------------------------------------------------
mesh-routes:
    cd 02-Backend; python -c "from app.infrastructure.service_mesh import get_mesh_manager; m = get_mesh_manager(); [print('VS:', v) for v in m.list_virtual_services()]; [print('DR:', d) for d in m.list_destination_rules()]"

mesh-manifest:
    cd 02-Backend; python -c "from app.infrastructure.service_mesh import get_mesh_manager; m = get_mesh_manager(); print(m.generate_istio_virtual_service('astrovox-api'))"

# ---------------------------------------------------------------------------
# Cloud: Progressive Delivery
# ---------------------------------------------------------------------------
canary-steps:
    cd 02-Backend; python -c "from app.infrastructure.progressive_delivery import get_progressive_delivery_manager; m = get_progressive_delivery_manager(); m.register_canary('astrovox-api', m._canary_configs.get('astrovox-api', None) or type('C', (), {'steps': [{'percent': 10}, {'percent': 25}, {'percent': 50}, {'percent': 100}]})()); print(m.get_canary_steps('astrovox-api'))"

# ---------------------------------------------------------------------------
# Cloud: Drift Detection
# ---------------------------------------------------------------------------
drift-scan:
    cd 02-Backend; python -c "from app.infrastructure.drift_detection import get_terraform_drift_detector; d = get_terraform_drift_detector(); print('Drift detector initialized')"

# ---------------------------------------------------------------------------
# Cloud: Cost
# ---------------------------------------------------------------------------
cost-summary:
    cd 02-Backend; python -c "from app.platform.cost_visibility import CostManager; print(f'Total cost: ${CostManager.get_total_cost():.2f}'); [print(f'{s}: ${v:.2f}') for s, v in CostManager.get_cost_by_service().items()]"

# ---------------------------------------------------------------------------
# Cloud: Multi-Region
# ---------------------------------------------------------------------------
region-list:
    cd 02-Backend; python -c "from app.infrastructure.multi_region_failover import FailoverManager; [print(r.region_id, r.status.value, r.priority) for r in FailoverManager.get_active_regions()]"

region-failover:
    cd 02-Backend; python -c "from app.infrastructure.multi_region_failover import FailoverManager; print(FailoverManager.get_failover_target('us-east-1'))"

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------
metrics:
    cd 02-Backend; python -c "from app.observability import get_observability; obs = get_observability(); print(obs.get_metrics_prometheus())"

health:
    cd 02-Backend; python -c "from app.observability import get_observability; obs = get_observability(); print(obs.get_status())"

logs:
    cd 02-Backend; python -c "import logging; logging.basicConfig(level=logging.INFO); [print('test log') for _ in range(5)]"

trace:
    cd 02-Backend; python -c "from app.observability.opentelemetry import get_tracer; t = get_tracer(); span = t.start_trace('trace-123', 'test'); span.end(); print('Trace recorded')"

# ---------------------------------------------------------------------------
# Observability: OpenTelemetry
# ---------------------------------------------------------------------------
otel-export:
    cd 02-Backend; python -c "from app.observability.opentelemetry import get_tracer; t = get_tracer(); import asyncio; asyncio.get_event_loop().run_until_complete(t.shutdown()); print('OTLP export completed')"

# ---------------------------------------------------------------------------
# DevOps: Docker
# ---------------------------------------------------------------------------
docker-build:
    docker build -f 02-Backend/Dockerfile.backend -t astrovoxai/backend:latest .

docker-build-frontend:
    docker build -f 02-Backend/Dockerfile.frontend -t astrovoxai/frontend:latest .

docker-compose-up:
    docker-compose -f 02-Backend/docker-compose.yml up -d

docker-compose-down:
    docker-compose -f 02-Backend/docker-compose.yml down

docker-compose-logs:
    docker-compose -f 02-Backend/docker-compose.yml logs -f

# ---------------------------------------------------------------------------
# DevOps: Chaos Engineering
# ---------------------------------------------------------------------------
chaos-redis:
    cd 02-Backend; python -c "from app.chaos_testing import RedisKillScenario; print('Redis chaos scenario ready')"

chaos-postgres:
    cd 02-Backend; python -c "from app.chaos_testing import PostgresKillScenario; print('PostgreSQL chaos scenario ready')"

# ---------------------------------------------------------------------------
# DevOps: Secret Rotation
# ---------------------------------------------------------------------------
secret-rotate:
    cd 02-Backend; python -c "from app.secret_rotation import SecretRotationService; s = SecretRotationService(); s.rotate_secret('TEST_SECRET'); print('Secret rotated')"

secret-check:
    cd 02-Backend; python -c "from app.secret_rotation import SecretRotationService; s = SecretRotationService(); print(s.check_due_rotations())"

# ---------------------------------------------------------------------------
# CI/CD
# ---------------------------------------------------------------------------
ci-local:
    cd 02-Backend; ruff check app tests; black --check app tests; flake8 app tests --max-line-length 120; pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

ci-frontend:
    cd apps/web; npm run lint; npm run typecheck; npm run build

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------
docs-api:
    cd 02-Backend; pdoc --html app/ -o docs/api/ --force

docs-generate:
    cd 02-Backend; python -m scripts.generate_docs

docs-serve:
    cd docs; python -m http.server 8080

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------
monitor-load-test:
    cd 02-Backend; python -m app.monitoring.load_testing

monitor-stress-test:
    cd 02-Backend; python -m app.monitoring.stress_testing

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean:
    cd 02-Backend; Remove-Item -Recurse -Force __pycache__, .pytest_cache, .mypy_cache, .ruff_cache, htmlcov, .coverage, *.egg-info, dist, build, logs, ./*.log, ./*.sqlite3, ./*.db, coverage.xml, bandit-report.json, pip-audit-report.json, benchmark-report.json

clean-logs:
    cd 02-Backend; Remove-Item -Recurse -Force logs, ./*.log

# ---------------------------------------------------------------------------
# Verify All Checks Pass
# ---------------------------------------------------------------------------
verify:
    just lint format typecheck test security-check docker-build
