#!/bin/bash
# AstrovoxAI Log Viewer
# Usage: ./scripts/logs.sh [service] [lines]

SERVICE=${1:-backend}
LINES=${2:-50}

case $SERVICE in
    backend)
        docker-compose logs --tail=$LINES -f backend
        ;;
    frontend)
        docker-compose logs --tail=$LINES -f frontend
        ;;
    redis)
        docker-compose logs --tail=$LINES -f redis
        ;;
    postgres)
        docker-compose logs --tail=$LINES -f postgres
        ;;
    all)
        docker-compose logs --tail=$LINES -f
        ;;
    *)
        echo "Usage: $0 [backend|frontend|redis|postgres|all] [lines]"
        exit 1
        ;;
esac
