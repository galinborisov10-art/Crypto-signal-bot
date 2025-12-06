#!/bin/bash

# DigitalOcean Deployment Script for Crypto Signal Bot
# Author: GitHub Copilot
# Date: 2025-11-25

echo "🚀 DigitalOcean Deployment Script"
echo "=================================="
echo ""

# Prompt for server IP
read -p "Enter your DigitalOcean Droplet IP: " SERVER_IP

if [ -z "$SERVER_IP" ]; then
    echo "❌ Error: Server IP is required"
    exit 1
fi

echo ""
echo "📦 Step 1: Connecting to server..."
ssh root@$SERVER_IP << 'ENDSSH'

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install Python 3.12 and dependencies
echo "🐍 Installing Python 3.12 and system libraries..."
apt install -y python3.12 python3.12-venv python3-pip git build-essential \
    fonts-dejavu fonts-liberation libfreetype6-dev libpng-dev pkg-config

# Clone repository
echo "📥 Cloning repository..."
cd /root
if [ -d "Crypto-signal-bot" ]; then
    echo "⚠️  Repository already exists, pulling latest changes..."
    cd Crypto-signal-bot
    git pull
else
    git clone https://github.com/galinborisov10-art/Crypto-signal-bot.git
    cd Crypto-signal-bot
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Validate dependencies
echo "✅ Validating dependencies..."
PTB_VERSION=$(python3 -m pip show python-telegram-bot 2>/dev/null | grep Version | awk '{print $2}')
if [ -n "$PTB_VERSION" ]; then
  echo "  📦 python-telegram-bot: $PTB_VERSION"
else
  echo "  ⚠️  python-telegram-bot installation check skipped"
fi

# Clear Python cache
echo "🗑️  Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo "  ✅ Python cache cleared"

# Create systemd service
echo "⚙️  Creating systemd service..."
cat > /etc/systemd/system/crypto-bot.service << 'EOF'
[Unit]
Description=Crypto Signal Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Crypto-signal-bot
Environment="PATH=/root/Crypto-signal-bot/venv/bin"
ExecStart=/root/Crypto-signal-bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/root/Crypto-signal-bot/bot.log
StandardError=append:/root/Crypto-signal-bot/bot.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo "🚀 Starting bot service..."
systemctl enable crypto-bot
systemctl start crypto-bot

# Wait for service to start
sleep 3

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
systemctl status crypto-bot --no-pager

# Verify deployment with health check
echo ""
echo "🔍 Running health check..."
if [ -f health-check.sh ]; then
  chmod +x health-check.sh
  ./health-check.sh
else
  echo "⚠️  Health check script not found, skipping validation"
fi

echo ""
echo "📋 Useful commands:"
echo "  View logs: journalctl -u crypto-bot -f"
echo "  Restart: systemctl restart crypto-bot"
echo "  Stop: systemctl stop crypto-bot"
echo "  Status: systemctl status crypto-bot"

ENDSSH

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Next steps:"
echo "1. SSH to your server: ssh root@$SERVER_IP"
echo "2. Check bot status: systemctl status crypto-bot"
echo "3. View logs: journalctl -u crypto-bot -f"
