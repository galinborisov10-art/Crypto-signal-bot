#!/bin/bash

# 🚀 MANUAL DEPLOYMENT SCRIPT
# Използвай този скрипт когато трябва да deploy-неш ръчно

echo "🚀 Starting manual deployment..."

# Navigate to bot directory
cd /root/Crypto-signal-bot || exit 1

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Restart the bot service
echo "🔄 Restarting bot service..."
systemctl restart crypto-bot

# Check status
echo "✅ Checking bot status..."
sleep 2
systemctl status crypto-bot --no-pager

echo ""
echo "✅ Deployment complete!"
echo "📊 Check bot status: systemctl status crypto-bot"
echo "📋 Check logs: journalctl -u crypto-bot -f"
