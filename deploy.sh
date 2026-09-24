#!/bin/bash
set -euo pipefail

echo "=== AstrovoxAI Deployment Helper ==="

check_command() {
  if ! command -v "$1" &> /dev/null; then
    echo "ERROR: $1 is not installed or not in PATH"
    exit 1
  fi
}

check_command docker
check_command kubectl
check_command helm

ENVIRONMENT="${1:-staging}"
TAG="${2:-latest}"

echo "Environment: $ENVIRONMENT"
echo "Image Tag: $TAG"

case "$ENVIRONMENT" in
  staging)
    CLUSTER="astrovox-staging"
    NAMESPACE="astrovox-staging"
    ;;
  production)
    CLUSTER="astrovox-prod"
    NAMESPACE="astrovox"
    ;;
  *)
    echo "Unknown environment: $ENVIRONMENT"
    echo "Usage: $0 [staging|production] [tag]"
    exit 1
    ;;
esac

echo "Updating kubeconfig for $CLUSTER..."
aws eks update-kubeconfig --name "$CLUSTER" --region us-east-1

echo "Deploying to $ENVIRONMENT..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -n "$NAMESPACE"

echo "Waiting for backend rollout..."
kubectl rollout status deployment/astrovox-backend -n "$NAMESPACE" --timeout=10m

echo "Waiting for frontend rollout..."
kubectl rollout status deployment/astrovox-frontend -n "$NAMESPACE" --timeout=10m

echo "Running smoke tests..."
kubectl run smoke-test --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -f "https://${ENVIRONMENT}.astrovox.ai/health"

echo "=== Deployment Complete ==="
kubectl get pods -n "$NAMESPACE"
kubectl get services -n "$NAMESPACE"
kubectl get ingress -n "$NAMESPACE"
kubectl get hpa -n "$NAMESPACE"
