#!/bin/bash
set -euo pipefail

NAMESPACE=${1:-astrovox}
SECRET_NAME=${2:-astrovox-secrets}

NEW_KEY=$(openssl rand -hex 32)

kubectl create secret generic $SECRET_NAME \
  --namespace $NAMESPACE \
  --from-literal=OPENAI_API_KEY=$NEW_KEY \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secrets rotated successfully."
