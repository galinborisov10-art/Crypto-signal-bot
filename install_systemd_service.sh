#!/bin/bash

# ============================================
# SYSTEMD SERVICE SETUP
# ============================================
# Инсталира systemd service за бота

SERVICE_FILE="crypto-signal-bot.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "🔧 Installing systemd service..."

# Copy service file
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable crypto-signal-bot.service

echo "✅ Service installed!"
echo ""
echo "📋 Available commands:"
echo "   sudo systemctl start crypto-signal-bot    - Start bot"
echo "   sudo systemctl stop crypto-signal-bot     - Stop bot"
echo "   sudo systemctl restart crypto-signal-bot  - Restart bot"
echo "   sudo systemctl status crypto-signal-bot   - Check status"
echo "   journalctl -u crypto-signal-bot -f        - View logs"
echo ""
echo "💡 Service will auto-restart on crash and auto-start on reboot!"
