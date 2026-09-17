#!/bin/bash
set -euo pipefail

NAMESPACE=${1:-astrovox}
RELEASE_NAME=${2:-astrovox}
CHART_PATH=${3:-./helm}

echo "Deploying $RELEASE_NAME to namespace $NAMESPACE..."
helm dependency build $CHART_PATH
helm upgrade --install $RELEASE_NAME $CHART_PATH \
  --namespace $NAMESPACE \
  --create-namespace \
  --wait \
  --timeout 5m

echo "Deployment complete."
