#!/bin/bash
set -euo pipefail

# AstrovoxAI DR Verification Script
# Usage: ./scripts/dr-verify.sh

echo "=========================================="
echo "AstrovoxAI DR Verification"
echo "=========================================="

# 1. Verify database connectivity
echo "Checking database connectivity..."
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

if command -v pg_isready > /dev/null 2>&1; then
  if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" > /dev/null 2>&1; then
    echo "✓ Database is accessible"
  else
    echo "✗ Database is NOT accessible"
    exit 1
  fi
else
  echo "⚠ pg_isready not available, skipping DB check"
fi

# 2. Verify Redis connectivity
echo "Checking Redis connectivity..."
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

if command -v redis-cli > /dev/null 2>&1; then
  if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping > /dev/null 2>&1; then
    echo "✓ Redis is accessible"
  else
    echo "✗ Redis is NOT accessible"
    exit 1
  fi
else
  echo "⚠ redis-cli not available, skipping Redis check"
fi

# 3. Verify Kubernetes deployments
echo "Checking Kubernetes deployments..."
if command -v kubectl > /dev/null 2>&1; then
  kubectl get nodes > /dev/null 2>&1 || echo "⚠ kubectl not configured"
  kubectl get deployments -n astrovox > /dev/null 2>&1 || echo "⚠ Cannot get deployments"
else
  echo "⚠ kubectl not available, skipping K8s checks"
fi

# 4. Verify backup integrity
echo "Checking backup integrity..."
BACKUP_DIR="./backups"
if [ -d "${BACKUP_DIR}" ]; then
  BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "*.sql.gz" -type f | wc -l)
  echo "✓ Found ${BACKUP_COUNT} database backups"

  if [ "${BACKUP_COUNT}" -gt 0 ]; then
    LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | head -1)
    if [ -n "${LATEST_BACKUP}" ]; then
      echo "✓ Latest backup: ${LATEST_BACKUP}"
      echo "  Size: $(du -h "${LATEST_BACKUP}" | cut -f1)"
    fi
  fi
else
  echo "⚠ Backup directory not found: ${BACKUP_DIR}"
fi

# 5. Verify monitoring
echo "Checking monitoring..."
if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
  echo "✓ Prometheus is healthy"
else
  echo "⚠ Prometheus health check failed"
fi

if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
  echo "✓ Grafana is healthy"
else
  echo "⚠ Grafana health check failed"
fi

# 6. Summary
echo ""
echo "=========================================="
echo "DR Verification Complete"
echo "=========================================="
