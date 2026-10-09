#!/bin/bash
set -euo pipefail

# AstrovoxAI Health Check Script
# Usage: ./scripts/health-check.sh [url]

URL="${1:-http://localhost:8000}"
CHECKS_PASSED=0
CHECKS_FAILED=0

echo "=========================================="
echo "AstrovoxAI Health Check"
echo "=========================================="
echo ""

check() {
  local name=$1
  local command=$2
  local expected=$3

  if eval "$command" > /dev/null 2>&1; then
    echo "✓ $name"
    ((CHECKS_PASSED++))
  else
    echo "✗ $name"
    ((CHECKS_FAILED++))
  fi
}

# Backend health
check "Backend health" "curl -s -f $URL/health | grep -q healthy" "healthy"
check "Backend readiness" "curl -s -f $URL/health/readiness | grep -q ready" "ready"
check "Backend liveness" "curl -s -f $URL/health/liveness | grep -q alive" "alive"

# Metrics endpoint
check "Prometheus metrics" "curl -s -f $URL/metrics | grep -q http_requests_total" "metrics"

# API documentation
check "API docs" "curl -s -f $URL/docs | grep -q Swagger" "swagger"

# Optional: Frontend
if curl -s -f "http://localhost" > /dev/null 2>&1; then
  check "Frontend health" "curl -s -f http://localhost | grep -q html" "html"
fi

echo ""
echo "=========================================="
echo "Checks passed: $CHECKS_PASSED"
echo "Checks failed: $CHECKS_FAILED"
echo "=========================================="

if [ $CHECKS_FAILED -eq 0 ]; then
  echo "✓ All systems healthy"
  exit 0
else
  echo "✗ Some systems unhealthy"
  exit 1
fi
