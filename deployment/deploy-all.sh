#!/bin/bash

# ============================================
# ASTRAVOX-AI Complete Deployment Script
# Deploys all services with zero downtime
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 ASTRAVOX-AI Complete Deployment${NC}"
echo "=========================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Function to check service health
check_health() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $service to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$port/health > /dev/null; then
            echo -e "${GREEN}✓ $service is ready${NC}"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ $service failed to start${NC}"
    return 1
}

# Step 1: Backup current database
echo -e "${BLUE}Step 1: Backing up databases...${NC}"
./scripts/backup-all-databases.sh

# Step 2: Pull latest code
echo -e "${BLUE}Step 2: Pulling latest code...${NC}"
git pull origin main

# Step 3: Install/update dependencies
echo -e "${BLUE}Step 3: Installing dependencies...${NC}"
npm ci --production=false

# Step 4: Run database migrations
echo -e "${BLUE}Step 4: Running database migrations...${NC}"
npm run migrate

# Step 5: Build frontend assets
echo -e "${BLUE}Step 5: Building frontend...${NC}"
npm run build

# Step 6: Start services with PM2
echo -e "${BLUE}Step 6: Starting services...${NC}"

# Stop existing services
pm2 stop astravox-api astravox-worker astravox-cron 2>/dev/null || true

# Start API server
pm2 start backend/server.js --name astravox-api --instances max --exec-mode cluster

# Start queue workers
pm2 start backend/workers/queueWorker.js --name astravox-worker
pm2 start backend/workers/emailWorker.js --name astravox-email
pm2 start backend/workers/aiWorker.js --name astravox-ai

# Start cron jobs
pm2 start backend/cron/index.js --name astravox-cron

# Save PM2 configuration
pm2 save

# Step 7: Wait for services to be ready
echo -e "${BLUE}Step 7: Verifying services...${NC}"
sleep 10

check_health "API Server" 5000
check_health "WebSocket" 5001

# Step 8: Reload Nginx
echo -e "${BLUE}Step 8: Reloading Nginx...${NC}"
sudo nginx -t && sudo systemctl reload nginx

# Step 9: Clear Redis cache
echo -e "${BLUE}Step 9: Clearing Redis cache...${NC}"
redis-cli FLUSHALL

# Step 10: Run smoke tests
echo -e "${BLUE}Step 10: Running smoke tests...${NC}"
npm run test:smoke

# Step 11: Notify deployment success
echo -e "${BLUE}Step 11: Sending deployment notification...${NC}"
curl -X POST https://api.astravox.ai/webhooks/deployment \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"success\",\"version\":\"$(git rev-parse HEAD)\",\"timestamp\":\"$(date -Iseconds)\"}"

# Step 12: Display deployment summary
echo ""
echo -e "${GREEN}=========================================="
echo -e "✅ DEPLOYMENT COMPLETE!"
echo -e "==========================================${NC}"
echo ""
echo "Service Status:"
pm2 status
echo ""
echo "Active Connections:"
netstat -tulpn | grep -E ':(5000|5001|6379|5432|27017)' || true
echo ""
echo "Deployment Details:"
echo "  Version: $(git rev-parse --short HEAD)"
echo "  Branch: $(git branch --show-current)"
echo "  Deployed: $(date)"
echo "  URL: https://astravox.ai"
echo ""
echo -e "${YELLOW}Monitor with: pm2 monit${NC}"
echo -e "${YELLOW}View logs: pm2 logs astravox-api${NC}"
