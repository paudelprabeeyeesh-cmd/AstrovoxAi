#!/bin/bash
set -euo pipefail

ENV=${1:-production}
echo "Deploying AstrovoxAI to $ENV environment..."

command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "Helm required"; exit 1; }

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Building containers..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

echo "Running database migrations..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend python -m alembic upgrade head || true

echo "Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "Waiting for health check..."
sleep 5
if ! curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "Health check failed"
    exit 1
fi

echo "Deploying to Kubernetes..."
NAMESPACE=${K8S_NAMESPACE:-astrovox}
RELEASE_NAME=${HELM_RELEASE_NAME:-astrovox}
CHART_PATH=./helm

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
helm dependency build "$CHART_PATH"
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --wait \
  --timeout 5m

echo "Running post-deployment health check..."
kubectl rollout status deployment/astrovox-backend -n "$NAMESPACE" --timeout=300s
kubectl get pods -n "$NAMESPACE"

echo "Deployment complete!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost"
echo "Kubernetes namespace: $NAMESPACE"
