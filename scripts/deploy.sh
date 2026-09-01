#!/bin/bash
# AstrovoxAI Deployment Script
# Usage: ./scripts/deploy.sh [environment]

set -e

ENV=${1:-production}
echo "Deploying AstrovoxAI to $ENV environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose required"; exit 1; }

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Build and deploy
echo "Building containers..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

echo "Running database migrations..."
docker-compose run --rm backend python -m alembic upgrade head 2>/dev/null || true

echo "Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "Waiting for health check..."
sleep 5
curl -f http://localhost:8000/health || { echo "Health check failed"; exit 1; }

echo "Deployment complete!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost"
