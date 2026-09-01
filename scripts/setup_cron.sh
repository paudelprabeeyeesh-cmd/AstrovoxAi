#!/bin/bash
# AstrovoxAI Cron Job Setup
# Usage: ./scripts/setup_cron.sh

set -e

echo "Setting up cron jobs for AstrovoxAI..."

# Create cron entries
CRON_FILE="/tmp/astrovox_cron"
cat > $CRON_FILE << EOF
# AstrovoxAI automated tasks

# Daily backup at 2 AM
0 2 * * * cd /opt/astrovox-ai && ./scripts/backup.sh >> /var/log/astrovox-ai/backup.log 2>&1

# System monitoring every 5 minutes
*/5 * * * * cd /opt/astrovox-ai && ./scripts/system_monitor.sh >> /var/log/astrovox-ai/monitor.log 2>&1

# Health check every minute
* * * * * curl -sf http://localhost:8000/health > /dev/null || echo "$(date): Health check failed" >> /var/log/astrovox-ai/health.log

# Log rotation check daily
0 0 * * * /usr/sbin/logrotate /etc/logrotate.d/astrovox-ai

# Weekly security scan (Sundays at 3 AM)
0 3 * * 0 cd /opt/astrovox-ai && docker-compose exec -T backend python -m pytest tests/ -v --tb=short >> /var/log/astrovox-ai/tests.log 2>&1
EOF

# Install cron jobs
crontab -u astrovox $CRON_FILE
rm $CRON_FILE

echo "Cron jobs installed:"
crontab -u astrovox -l
