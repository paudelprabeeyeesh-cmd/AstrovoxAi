#!/bin/bash
set -euo pipefail

# AstrovoxAI Disaster Recovery Failover Script
# Usage: ./scripts/dr-failover.sh [primary|dr]

ENVIRONMENT="${1:-primary}"
AWS_REGION="us-east-1"
DR_REGION="us-west-2"
PROJECT_NAME="astrovox"
CLUSTER_NAME="${PROJECT_NAME}-prod"

echo "=========================================="
echo "AstrovoxAI DR Failover"
echo "Environment: ${ENVIRONMENT}"
echo "=========================================="

if [ "${ENVIRONMENT}" == "dr" ]; then
  echo "Activating DR region (${DR_REGION})..."

  # Update kubeconfig for DR region
  aws eks update-kubeconfig --name "${CLUSTER_NAME}" --region "${DR_REGION}"

  # Scale up DR cluster
  kubectl scale deployment/astrovox-backend -n astrovox --replicas=5
  kubectl scale deployment/astrovox-frontend -n astrovox --replicas=3

  # Wait for rollout
  kubectl rollout status deployment/astrovox-backend -n astrovox --timeout=10m
  kubectl rollout status deployment/astrovox-frontend -n astrovox --timeout=10m

  echo "DR region activated successfully"
  echo "Next: Update DNS records to point to DR region"
else
  echo "Verifying primary region..."

  # Update kubeconfig for primary region
  aws eks update-kubeconfig --name "${CLUSTER_NAME}" --region "${AWS_REGION}"

  # Check cluster health
  kubectl get nodes
  kubectl get pods -n astrovox

  echo "Primary region verified"
fi
