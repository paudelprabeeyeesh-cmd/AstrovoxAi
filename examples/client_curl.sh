#!/usr/bin/env bash
# cURL examples for AstrovoxAI inference server
# Usage: bash examples/client_curl.sh [command]
# Commands: health, completion, chat, batch

set -euo pipefail

# Configuration
BASE_URL="${ASTROVOX_BASE_URL:-http://localhost:8001}"
API_KEY="${ASTROVOX_API_KEY:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Build auth header if API key is set
AUTH_HEADER=""
if [ -n "$API_KEY" ]; then
    AUTH_HEADER="-H \"Authorization: Bearer $API_KEY\""
fi

health() {
    info "Checking server health..."
    curl -s -X GET "${BASE_URL}/health" | jq .
    echo ""
    info "Checking readiness..."
    curl -s -X GET "${BASE_URL}/health/ready" | jq .
    echo ""
    info "Checking model status..."
    curl -s -X GET "${BASE_URL}/health/model" | jq .
}

completion() {
    local prompt="${1:-Hello, world!}"
    info "Sending completion request..."
    curl -s -X POST "${BASE_URL}/v1/completions" \
        -H "Content-Type: application/json" \
        $AUTH_HEADER \
        -d "{
            \"prompt\": \"$prompt\",
            \"max_tokens\": 100,
            \"temperature\": 1.0
        }" | jq .
}

chat() {
    local message="${1:-Tell me a story about AI}"
    info "Sending chat completion request..."
    curl -s -X POST "${BASE_URL}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        $AUTH_HEADER \
        -d "{
            \"messages\": [
                {\"role\": \"user\", \"content\": \"$message\"}
            ],
            \"max_tokens\": 100,
            \"temperature\": 1.0
        }" | jq .
}

batch() {
    info "Sending batch completion request..."
    curl -s -X POST "${BASE_URL}/v1/batch" \
        -H "Content-Type: application/json" \
        $AUTH_HEADER \
        -d '{
            "prompts": [
                "Hello",
                "World",
                "AI is"
            ],
            "max_tokens": 50,
            "temperature": 1.0
        }' | jq .
}

metrics() {
    info "Fetching Prometheus metrics..."
    curl -s -X GET "${BASE_URL}/metrics" | head -50
}

# Main command handler
case "${1:-help}" in
    health)
        health
        ;;
    completion)
        completion "${2:-Hello, world!}"
        ;;
    chat)
        chat "${2:-Tell me a story about AI}"
        ;;
    batch)
        batch
        ;;
    metrics)
        metrics
        ;;
    help|*)
        echo "Usage: $0 [command] [args]"
        echo ""
        echo "Commands:"
        echo "  health                  Check server health and readiness"
        echo "  completion [prompt]     Send text completion request"
        echo "  chat [message]          Send chat completion request"
        echo "  batch                   Send batch completion request"
        echo "  metrics                  Fetch Prometheus metrics"
        echo ""
        echo "Environment variables:"
        echo "  ASTROVOX_BASE_URL   Base URL for the inference server (default: http://localhost:8001)"
        echo "  ASTROVOX_API_KEY    API key for authentication (optional)"
        ;;
esac
