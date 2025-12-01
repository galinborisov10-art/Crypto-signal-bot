#!/bin/bash
# =============================================================================
# update_bot.sh - Server Update Script for Crypto Signal Bot
# =============================================================================
# This script updates the bot from GitHub and restarts it
# Usage: ./update_bot.sh
# =============================================================================

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 CRYPTO SIGNAL BOT - AUTO UPDATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed!"
    exit 1
fi

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ This directory is not a git repository!"
    exit 1
fi

echo "📥 Pulling latest code from GitHub..."
git fetch origin main
git reset --hard origin/main
echo "✅ Code updated successfully!"
echo ""

echo "📦 Installing/Updating dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt --upgrade --quiet
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt --upgrade --quiet
else
    echo "⚠️ pip not found, skipping dependency installation"
fi
echo "✅ Dependencies updated!"
echo ""

echo "🔄 Restarting bot..."
# Try PM2 first
if command -v pm2 &> /dev/null; then
    pm2 restart crypto-bot 2>/dev/null || pm2 start ecosystem.config.js
    echo "✅ Bot restarted via PM2!"
    echo ""
    echo "📋 Recent logs:"
    pm2 logs crypto-bot --lines 20 --nostream
# Try systemd
elif systemctl is-active --quiet crypto-bot.service 2>/dev/null; then
    sudo systemctl restart crypto-bot.service
    echo "✅ Bot restarted via systemd!"
# Fallback to direct restart
else
    # Kill existing bot process
    pkill -f "python.*bot.py" 2>/dev/null || true
    sleep 2
    
    # Start bot in background
    nohup python3 bot.py > bot.log 2>&1 &
    echo "✅ Bot restarted directly!"
    echo "📝 Logs available at: $SCRIPT_DIR/bot.log"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ UPDATE COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
