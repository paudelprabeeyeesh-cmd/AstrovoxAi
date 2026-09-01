#!/bin/bash
# AstrovoxAI System Monitoring Dashboard
# Usage: ./scripts/system_monitor.sh

echo "=== AstrovoxAI System Monitor ==="
echo "Timestamp: $(date)"
echo ""

# System info
echo "--- System Info ---"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p 2>/dev/null || uptime)"
echo "Load Average: $(cat /proc/loadavg 2>/dev/null || echo 'N/A')"
echo ""

# CPU
echo "--- CPU ---"
if command -v top >/dev/null 2>&1; then
    echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
fi
echo ""

# Memory
echo "--- Memory ---"
if [ -f /proc/meminfo ]; then
    total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    available=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    used=$((total - available))
    percent=$((used * 100 / total))
    echo "Memory: ${used}KB / ${total}KB (${percent}% used)"
fi
echo ""

# Disk
echo "--- Disk ---"
if command -v df >/dev/null 2>&1; then
    df -h / | tail -1 | awk '{print "Disk: $3 / $2 ($5 used)"}'
fi
echo ""

# Docker containers
echo "--- Docker Containers ---"
if command -v docker >/dev/null 2>&1; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers running"
fi
echo ""

# Network
echo "--- Network Connections ---"
if command -v ss >/dev/null 2>&1; then
    echo "Active connections: $(ss -tuln | wc -l)"
fi
echo ""

# AstrovoxAI specific
echo "--- AstrovoxAI Health ---"
if command -v curl >/dev/null 2>&1; then
    health=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{"status": "unreachable"}')
    echo "Backend: $health"
fi
