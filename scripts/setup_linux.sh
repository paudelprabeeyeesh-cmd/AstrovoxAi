#!/bin/bash
# AstrovoxAI Linux Setup Script
# Usage: ./scripts/setup_linux.sh

set -e

echo "=== AstrovoxAI Linux Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt-get install -y \
    curl \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    htop \
    jq

# Setup Docker
echo "Configuring Docker..."
systemctl enable docker
systemctl start docker

# Create astrovox user
if ! id "astrovox" &>/dev/null; then
    echo "Creating astrovox user..."
    useradd -m -s /bin/bash astrovox
    usermod -aG docker astrovox
fi

# Setup directories
echo "Setting up directories..."
mkdir -p /opt/astrovox-ai
mkdir -p /opt/astrovox-ai/storage
mkdir -p /opt/astrovox-ai/backups
mkdir -p /var/log/astrovox-ai

# Set permissions
chown -R astrovox:astrovox /opt/astrovox-ai
chown -R astrovox:astrovox /var/log/astrovox-ai

# Setup log rotation
cat > /etc/logrotate.d/astrovox-ai << EOF
/var/log/astrovox-ai/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 astrovox astrovox
}
EOF

# Setup systemd service
cat > /etc/systemd/system/astrovox-ai.service << EOF
[Unit]
Description=AstrovoxAI Backend
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/astrovox-ai
ExecStart=/usr/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose down
User=astrovox
Group=astrovox

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable astrovox-ai

echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Copy your project to /opt/astrovox-ai"
echo "2. Create .env file with your credentials"
echo "3. Run: systemctl start astrovox-ai"
echo "4. Configure Nginx with: certbot --nginx -d yourdomain.com"
